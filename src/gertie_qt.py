#!/usr/bin/env python3
"""
GERTIE Qt - Production Camera System with Gallery

Features:
- 8-camera grid display with real-time streaming
- Still capture functionality
- Gallery panel with auto-refresh
- Integrated layout with toggle
- Complete network command support for Pi cameras
"""

import sys
import os
import time
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, 
    QLabel, QVBoxLayout, QHBoxLayout, QStatusBar, 
    QPushButton, QSplitter, QProgressBar, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap, QImage

# Import our modules
from network_manager import NetworkManager
from gallery_panel import GalleryPanel
from camera_settings_dialog import CameraSettingsDialog
from config import get_ip_from_camera_id, SLAVES

# ============================================================================
# LOGGING SETUP - Outputs to stdout, captured by run_qt_with_logging.sh
# Logs go to: updatelog.txt (cumulative) + qt_latest.log (session)
# ============================================================================
gui_logger = logging.getLogger("GERTIE_GUI")
gui_logger.setLevel(logging.DEBUG)

# Console handler only - stdout captured by run_qt_with_logging.sh tee command
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # DEBUG level to capture all details
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [GUI:%(levelname)s] %(message)s', 
    datefmt='%H:%M:%S'
))
gui_logger.addHandler(console_handler)

# Resolution settings for exclusive mode
# Pi HQ Camera has 4:3 native sensor (4056x3040) - use 4:3 resolutions to avoid cropping!
NORMAL_RESOLUTION = (640, 480)    # 4:3 - efficient for 8-camera grid
EXCLUSIVE_RESOLUTION = (1280, 960)  # 4:3 HD - matches HQ camera native aspect ratio
ENABLE_RESOLUTION_SWITCHING = True  # Re-enabled: GUI freeze was from decode-on-signal, not resolution switching

gui_logger.info("Resolution config: NORMAL=%s, EXCLUSIVE=%s, SWITCHING=%s", 
                NORMAL_RESOLUTION, EXCLUSIVE_RESOLUTION, ENABLE_RESOLUTION_SWITCHING)


class CameraWidget(QWidget):
    """Widget representing a single camera with video feed and controls"""
    
    capture_requested = Signal(int, str)
    settings_requested = Signal(int, str)  # camera_id, ip
    
    def __init__(self, camera_id: int, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.ip = get_ip_from_camera_id(camera_id)  # Use config for correct IP
        self._last_size = None  # Cache for resize detection
        self._current_pixmap = None  # Cache current frame
        self._exclusive_mode = False  # Exclusive mode flag for proper scaling
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Video display - scaling handled in update_frame based on mode
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                background-color: #000;
            }
        """)
        self.video_label.setMinimumSize(200, 150)
        # NOTE: setScaledContents disabled - we handle scaling in update_frame()
        # This allows proper aspect ratio preservation in exclusive mode
        self.video_label.setScaledContents(False)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.video_label, 1)  # stretch factor
        
        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(5)
        
        cam_label = QLabel(f"REP{self.camera_id}")
        cam_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        controls.addWidget(cam_label)
        
        controls.addStretch()
        
        # Capture button
        self.capture_btn = QPushButton("📷")
        self.capture_btn.setFixedSize(30, 25)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #3b6; }
            QPushButton:pressed { background-color: #194; }
        """)
        self.capture_btn.clicked.connect(self._on_capture)
        controls.addWidget(self.capture_btn)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 25)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton:pressed { background-color: #444; }
        """)
        self.settings_btn.clicked.connect(self._on_settings)
        controls.addWidget(self.settings_btn)
        
        layout.addLayout(controls)
    
    def _on_capture(self):
        print(f"[DEBUG] CameraWidget._on_capture() called for camera {self.camera_id}, ip={self.ip}")
        self.capture_requested.emit(self.camera_id, self.ip)
    
    def _on_settings(self):
        self.settings_requested.emit(self.camera_id, self.ip)
    
    def set_exclusive_mode(self, enabled: bool):
        """Enable/disable exclusive mode for proper aspect ratio handling"""
        self._exclusive_mode = enabled
        self._last_label_size = None  # Force recalculation on mode change
        # Don't call update_frame here - the layout hasn't processed yet!
        # The display timer will update with correct size on next tick (50ms)
    
    def update_frame(self, pixmap: QPixmap):
        """Update video frame with proper aspect ratio scaling
        
        PERFORMANCE: Uses FastTransformation always to avoid GUI freeze.
        Only recalculates scale when label size changes.
        """
        if pixmap and not pixmap.isNull():
            self._current_pixmap = pixmap  # Cache for resize events
            
            # Get label size for scaling
            label_size = self.video_label.size()
            
            # PERFORMANCE: Always use FastTransformation to prevent GUI freeze
            # SmoothTransformation was causing freezes with rapid camera switching
            scaled = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            self.video_label.setPixmap(scaled)


class MainWindow(QMainWindow):
    """Main window with camera grid and gallery"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GERTIE Qt - Phase 3: Capture + Gallery")
        self.setGeometry(50, 50, 1600, 900)
        
        # Initialize systems
        self.network_manager = NetworkManager(mock_mode=False)
        self.network_manager.capture_completed.connect(self._on_capture_completed)
        self.network_manager.video_frame_received.connect(self._on_video_frame_received)
        self.network_manager.still_image_received.connect(self._on_still_image_received)
        self.network_manager.raw_image_received.connect(self._on_raw_image_received)
        
        # Real video frame buffers (camera_id -> latest frame)
        self.real_frames = {}  # Raw JPEG bytes for saving
        self.decoded_frames = {}  # Pre-decoded QPixmaps for display
        self.frame_dirty = set()  # Track which cameras have new frames
        
        # High-res captures directory
        self.hires_captures_dir = "hires_captures"
        os.makedirs(self.hires_captures_dir, exist_ok=True)
        
        # State
        self.frame_count = 0
        self.start_time = time.time()
        self.paused = False
        self.captures_dir = "captures"
        os.makedirs(self.captures_dir, exist_ok=True)
        self.capture_count = 0
        self.current_frames = []
        
        # Exclusive mode (single camera enlarged view)
        self.exclusive_camera = None  # Camera ID (1-8) when in exclusive mode, None for normal view
        self._last_exclusive_switch = 0  # Timestamp for debouncing rapid switches
        self._hd_cameras = set()  # Track cameras switched to HD (need reset on exit)
        
        # Capture queue tracking (no cooldown - uses adaptive chunk sizing instead)
        self.pending_hires_count = 0  # Number of hi-res images pending
        self.capture_timeout_timer = None  # Timer to reset stuck captures
        
        # UI
        self._setup_ui()
        
        # Timer - OPTIMIZED: 50ms (20fps) is sufficient for preview
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frames)
        self.timer.start(50)
        
        print("="*70)
        print("GERTIE Qt - Production Network Mode")
        print("="*70)
        print("Keyboard Shortcuts:")
        print("  Space: Capture all cameras")
        print("  C: Capture all cameras (alternate)")
        print("  1-8: Toggle camera preview (exclusive mode)")
        print("  Escape: Show all cameras (exit exclusive)")
        print("  R: Restart all streams")
        print("  S: Open settings")
        print("  G: Toggle gallery")
        print("  Q: Quit")
        print("="*70)
        
        # Start video streams on all cameras after short delay
        # (ensures network manager is fully ready)
        QTimer.singleShot(2000, self._start_all_streams)
    
    def _start_all_streams(self):
        """Start video streaming on all cameras"""
        print("\n📡 Starting video streams on all cameras...")
        self.network_manager.send_start_all_streams()
    
    def _setup_ui(self):
        """Setup UI with splitter for camera/gallery"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout()
        central.setLayout(main_layout)
        
        # Splitter for cameras and gallery
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Camera grid
        cameras_widget = QWidget()
        cameras_layout = QVBoxLayout()
        cameras_widget.setLayout(cameras_layout)
        
        # Camera grid (2x4)
        self.camera_grid = QGridLayout()
        self.camera_grid.setSpacing(5)
        
        self.camera_widgets = []
        for i in range(8):
            widget = CameraWidget(i + 1)
            widget.capture_requested.connect(self._on_camera_capture)
            widget.settings_requested.connect(self._on_camera_settings)
            self.camera_grid.addWidget(widget, i // 4, i % 4)
            self.camera_widgets.append(widget)
        
        cameras_layout.addLayout(self.camera_grid)
        
        # Bottom controls
        controls = QHBoxLayout()
        
        capture_all_btn = QPushButton("📷 Capture All (C)")
        capture_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #25a;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #36b; }
            QPushButton:pressed { background-color: #149; }
        """)
        capture_all_btn.clicked.connect(self._on_capture_all)
        controls.addWidget(capture_all_btn)
        
        controls.addStretch()
        
        # Toggle gallery button
        self.toggle_gallery_btn = QPushButton("📁 Gallery (G)")
        self.toggle_gallery_btn.setCheckable(True)
        self.toggle_gallery_btn.setChecked(True)
        self.toggle_gallery_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #555;
                border: 2px solid #66f;
            }
            QPushButton:hover { background-color: #555; }
        """)
        self.toggle_gallery_btn.clicked.connect(self._toggle_gallery)
        controls.addWidget(self.toggle_gallery_btn)
        
        # Hi-res upload progress: label + bar
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #4a9eff; font-size: 10px;")
        self.progress_label.hide()
        controls.addWidget(self.progress_label)
        
        self.upload_progress = QProgressBar()
        self.upload_progress.setFixedSize(80, 14)
        self.upload_progress.setTextVisible(False)
        self.upload_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 2px;
            }
        """)
        self.upload_progress.setRange(0, 8)
        self.upload_progress.setValue(0)
        self.upload_progress.hide()
        controls.addWidget(self.upload_progress)
        
        cameras_layout.addLayout(controls)
        
        # Right side - Gallery (resizable via splitter)
        self.gallery = GalleryPanel(self.hires_captures_dir)
        self.gallery.setMinimumWidth(150)
        
        # Add to splitter - enables drag to resize
        self.splitter.addWidget(cameras_widget)
        self.splitter.addWidget(self.gallery)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setChildrenCollapsible(False)  # Prevent fully collapsing
        
        main_layout.addWidget(self.splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _update_frames(self):
        """Update camera frames - decode and display only dirty frames
        
        CRITICAL: Decoding happens HERE (max 8 per 50ms) not in signal handler.
        This keeps GUI responsive by limiting decode work per timer tick.
        """
        if self.paused:
            return
        
        # Only update widgets with NEW frames - decode here, not in signal handler
        dirty_cameras = list(self.frame_dirty)
        self.frame_dirty.clear()
        
        for camera_id in dirty_cameras:
            if camera_id in self.real_frames:
                data = self.real_frames[camera_id]
                
                # Decode JPEG to QPixmap (max 8 per timer tick = 160/sec vs 200+/sec before)
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    self.decoded_frames[camera_id] = pixmap
                    widget = self.camera_widgets[camera_id - 1]
                    widget.update_frame(pixmap)
                    
                    # Log decoded frame dimensions periodically for resolution debugging
                    if not hasattr(self, '_decode_log_count'):
                        self._decode_log_count = {}
                    self._decode_log_count[camera_id] = self._decode_log_count.get(camera_id, 0) + 1
                    if self._decode_log_count[camera_id] % 200 == 1:  # First frame and every 200th
                        gui_logger.info("[DECODE] Camera %d: decoded frame %dx%d (frame #%d)", 
                                       camera_id, pixmap.width(), pixmap.height(), 
                                       self._decode_log_count[camera_id])
                
                # Store bytes for frame capture
                if len(self.current_frames) < 8:
                    self.current_frames = [None] * 8
                self.current_frames[camera_id - 1] = data
        
        self.frame_count += 1
        
        # Update status less frequently (every 60 frames)
        if self.frame_count % 60 == 0:
            elapsed = time.time() - self.start_time
            gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
            self.status_bar.showMessage(
                f"FPS: {gui_fps:.1f} | Frames: {self.frame_count} | Captures: {self.capture_count}"
            )
    
    def _on_camera_capture(self, camera_id: int, ip: str):
        """Handle single camera capture - creates preview thumbnail and sends capture command"""
        print(f"\n📷 [DEBUG] _on_camera_capture RECEIVED: camera {camera_id} ({ip})")
        gui_logger.info("[CAPTURE] Single capture requested for camera %d (%s)", camera_id, ip)
        
        # INSTANT: Create preview thumbnail from current video frame (like Capture All does)
        if hasattr(self, 'gallery') and camera_id in self.decoded_frames:
            preview_pixmap = self.decoded_frames[camera_id]
            if preview_pixmap and not preview_pixmap.isNull():
                # Scale to thumbnail size (175x113)
                thumb = preview_pixmap.scaled(175, 113,
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.FastTransformation)
                # Add to gallery as preview
                self.gallery.add_preview_thumbnail(camera_id, thumb)
        
        # Track pending hi-res capture
        self.pending_hires_count += 1
        
        # Show progress bar for single capture too
        self.upload_progress.setRange(0, self.pending_hires_count)
        received = self.upload_progress.maximum() - self.pending_hires_count + 1
        self.upload_progress.setValue(received - 1)
        self.upload_progress.show()
        self.progress_label.setText(f"{received - 1}/{self.pending_hires_count}")
        self.progress_label.show()
        
        # Send actual capture command (hi-res image will arrive later via TCP)
        self.network_manager.send_capture_command(ip, camera_id)
        
        self.status_bar.showMessage(f"Capturing camera {camera_id}...", 2000)
    
    def _on_camera_settings(self, camera_id: int, ip: str):
        """Handle camera settings dialog"""
        camera_name = f"REP{camera_id}"
        print(f"\n⚙️ Opening settings for {camera_name} ({ip})")
        dialog = CameraSettingsDialog(ip, camera_name, self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()
    
    def _on_settings_applied(self, ip: str, settings: dict):
        """Handle settings applied"""
        print(f"  ✓ Settings applied for {ip}")
        # Send settings to camera via NetworkManager
        self.network_manager.send_settings(ip, settings)
    
    def _on_capture_all(self):
        """Handle capture all - INSTANT preview thumbnails from video frames!
        
        Uses adaptive chunk sizing in network receiver to handle queue depth.
        Smaller chunks when busy = GUI stays responsive.
        """
        
        # Queue depth protection - allow multiple captures but limit queue
        MAX_PENDING = 24  # Max 24 hi-res images in flight (3 batches)
        
        if self.pending_hires_count >= MAX_PENDING:
            print(f"⚠️ Queue full ({self.pending_hires_count} images pending) - please wait...")
            self.status_bar.showMessage(f"⏳ Queue full - {self.pending_hires_count} images downloading...", 2000)
            return
        
        # Add 8 more to pending count
        self.pending_hires_count += 8
        
        # Show progress bar and label
        self.upload_progress.setRange(0, self.pending_hires_count)
        self.upload_progress.setValue(0)
        self.upload_progress.show()
        self.progress_label.setText(f"0/{self.pending_hires_count}")
        self.progress_label.show()
        
        print(f"\n📷 Capturing... ({self.pending_hires_count} pending)")
        
        # INSTANT: Create preview thumbnails from current video frames
        if hasattr(self, 'gallery'):
            for camera_id in range(1, 9):
                if camera_id in self.decoded_frames:
                    preview_pixmap = self.decoded_frames[camera_id]
                    if preview_pixmap and not preview_pixmap.isNull():
                        # Scale to thumbnail size (25% larger: 175x113)
                        thumb = preview_pixmap.scaled(175, 113,
                                                      Qt.AspectRatioMode.KeepAspectRatio,
                                                      Qt.TransformationMode.FastTransformation)
                        # Add to gallery as preview
                        self.gallery.add_preview_thumbnail(camera_id, thumb)
        
        # Send actual capture command (hi-res images will arrive later)
        self.network_manager.send_capture_all()
        
        # Start timeout timer - reset if images don't arrive within 20 seconds
        if self.capture_timeout_timer:
            self.capture_timeout_timer.stop()
        self.capture_timeout_timer = QTimer()
        self.capture_timeout_timer.setSingleShot(True)
        self.capture_timeout_timer.timeout.connect(self._on_capture_timeout)
        self.capture_timeout_timer.start(20000)  # 20 seconds
    
    def _on_capture_timeout(self):
        """Handle capture timeout - reset progress if images don't arrive"""
        if self.pending_hires_count > 0:
            missing = self.pending_hires_count
            print(f"\n⚠️ TIMEOUT: {missing} images did not arrive - resetting progress")
            self.status_bar.showMessage(f"⚠️ Timeout: {missing} images missing - cameras may need restart", 5000)
            
            # Reset progress
            self.pending_hires_count = 0
            self.upload_progress.hide()
            self.progress_label.hide()
    
    def _save_frame_capture(self, camera_id: int):
        """Save current frame from buffer - OPTIMIZED: direct JPEG bytes write"""
        try:
            if camera_id - 1 < len(self.current_frames):
                jpeg_data = self.current_frames[camera_id - 1]
                if jpeg_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    filename = f"{self.captures_dir}/rep{camera_id}_{timestamp}.jpg"
                    with open(filename, 'wb') as f:
                        f.write(jpeg_data)
                    self.capture_count += 1
                    print(f"  ✓ Saved: {filename}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    def _on_capture_completed(self, ip: str):
        """Network capture completed"""
        pass
    
    def _on_video_frame_received(self, ip: str, camera_id: int, data: bytes):
        """Handle incoming video frame - STORE ONLY, decode on display timer
        
        CRITICAL: Do NOT decode here! This runs ~200x/sec and blocks GUI.
        Just store raw bytes and mark dirty. Decode in _update_frames().
        """
        self.real_frames[camera_id] = data
        self.frame_dirty.add(camera_id)
        
        # Log first frame per camera (one-time only)
        if not hasattr(self, '_first_frame_logged'):
            self._first_frame_logged = set()
        if camera_id not in self._first_frame_logged:
            self._first_frame_logged.add(camera_id)
            print(f"  📹 First frame from camera {camera_id}: {len(data)} bytes")
            gui_logger.info("[FRAME] First frame from camera %d: %d bytes", camera_id, len(data))
        
        # Log frame size periodically for resolution debugging (every 500 frames per camera)
        if not hasattr(self, '_frame_log_count'):
            self._frame_log_count = {}
        self._frame_log_count[camera_id] = self._frame_log_count.get(camera_id, 0) + 1
        if self._frame_log_count[camera_id] % 500 == 0:
            gui_logger.debug("[FRAME] Camera %d: frame #%d, %d bytes", 
                           camera_id, self._frame_log_count[camera_id], len(data))
    
    def _on_still_image_received(self, camera_id: int, data: bytes, timestamp: str):
        """Handle incoming high-resolution still image from real camera"""
        try:
            # Save to hires_captures directory
            filename = f"{self.hires_captures_dir}/rep{camera_id}_{timestamp}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(data)
            
            size_kb = len(data) / 1024
            self.capture_count += 1
            
            # Get image dimensions for logging
            img_width, img_height = 0, 0
            aspect_ratio = "unknown"
            try:
                # Decode to get dimensions
                img = QImage()
                if img.loadFromData(data):
                    img_width = img.width()
                    img_height = img.height()
                    if img_height > 0:
                        ratio = img_width / img_height
                        if abs(ratio - 4/3) < 0.01:
                            aspect_ratio = "4:3 ✓"
                        elif abs(ratio - 16/9) < 0.01:
                            aspect_ratio = "16:9 ⚠️"
                        else:
                            aspect_ratio = f"{ratio:.2f}"
            except Exception as e:
                gui_logger.warning("[CAPTURE] Failed to get dimensions for camera %d: %s", camera_id, e)
            
            # Log capture with dimensions
            gui_logger.info("[CAPTURE] Camera %d: %s - %dx%d (%s) %.0fKB", 
                          camera_id, os.path.basename(filename), img_width, img_height, aspect_ratio, size_kb)
            
            # Decrement pending count and update progress bar
            if self.pending_hires_count > 0:
                self.pending_hires_count -= 1
                received = self.upload_progress.maximum() - self.pending_hires_count
                self.upload_progress.setValue(received)
                self.progress_label.setText(f"{received}/{self.upload_progress.maximum()}")
            
            # Show status
            if self.pending_hires_count > 0:
                print(f"  📸 Hi-res: {os.path.basename(filename)} ({size_kb:.0f}KB) {img_width}x{img_height} {aspect_ratio} [{self.pending_hires_count} left]")
            else:
                print(f"  📸 Hi-res: {os.path.basename(filename)} ({size_kb:.0f}KB) {img_width}x{img_height} {aspect_ratio} [done]")
                # All images received - stop timeout timer and hide progress
                if self.capture_timeout_timer:
                    self.capture_timeout_timer.stop()
                self.upload_progress.hide()
                self.progress_label.hide()
            
            # Link preview thumbnail to actual hi-res file
            if hasattr(self, 'gallery'):
                self.gallery.link_preview_to_file(camera_id, filename)
                
        except Exception as e:
            print(f"  ⚠️ Still save error for camera {camera_id}: {e}")
            gui_logger.error("[CAPTURE] Error saving camera %d: %s", camera_id, e)
    
    def _on_raw_image_received(self, camera_id: int, jpeg_data: bytes, dng_data: bytes, timestamp: str):
        """Handle incoming RAW capture (JPEG + DNG) from camera
        
        Saves both files and uses JPEG for gallery thumbnail.
        """
        try:
            # Save JPEG
            jpeg_filename = f"{self.hires_captures_dir}/rep{camera_id}_{timestamp}.jpg"
            with open(jpeg_filename, 'wb') as f:
                f.write(jpeg_data)
            
            # Save DNG (RAW)
            dng_filename = f"{self.hires_captures_dir}/rep{camera_id}_{timestamp}.dng"
            with open(dng_filename, 'wb') as f:
                f.write(dng_data)
            
            jpeg_kb = len(jpeg_data) / 1024
            dng_mb = len(dng_data) / 1024 / 1024
            self.capture_count += 1
            
            # Get JPEG dimensions for logging
            img_width, img_height = 0, 0
            aspect_ratio = "unknown"
            try:
                img = QImage()
                if img.loadFromData(jpeg_data):
                    img_width = img.width()
                    img_height = img.height()
                    if img_height > 0:
                        ratio = img_width / img_height
                        if abs(ratio - 4/3) < 0.01:
                            aspect_ratio = "4:3 ✓"
                        elif abs(ratio - 16/9) < 0.01:
                            aspect_ratio = "16:9 ⚠️"
                        else:
                            aspect_ratio = f"{ratio:.2f}"
            except Exception as e:
                gui_logger.warning("[CAPTURE] Failed to get dimensions for camera %d: %s", camera_id, e)
            
            # Log RAW capture
            gui_logger.info("[CAPTURE] RAW Camera %d: %s + %s - %dx%d (%s) JPEG=%.0fKB DNG=%.1fMB", 
                          camera_id, os.path.basename(jpeg_filename), os.path.basename(dng_filename),
                          img_width, img_height, aspect_ratio, jpeg_kb, dng_mb)
            
            # Update progress (RAW counts as 1 capture even though it's 2 files)
            if self.pending_hires_count > 0:
                self.pending_hires_count -= 1
                received = self.upload_progress.maximum() - self.pending_hires_count
                self.upload_progress.setValue(received)
                self.progress_label.setText(f"{received}/{self.upload_progress.maximum()}")
            
            # Show status
            if self.pending_hires_count > 0:
                print(f"  📸 RAW: {os.path.basename(jpeg_filename)} ({jpeg_kb:.0f}KB) + DNG ({dng_mb:.1f}MB) {img_width}x{img_height} {aspect_ratio} [{self.pending_hires_count} left]")
            else:
                print(f"  📸 RAW: {os.path.basename(jpeg_filename)} ({jpeg_kb:.0f}KB) + DNG ({dng_mb:.1f}MB) {img_width}x{img_height} {aspect_ratio} [done]")
                if self.capture_timeout_timer:
                    self.capture_timeout_timer.stop()
                self.upload_progress.hide()
                self.progress_label.hide()
            
            # Link preview thumbnail to JPEG file (not DNG)
            if hasattr(self, 'gallery'):
                self.gallery.link_preview_to_file(camera_id, jpeg_filename)
                
        except Exception as e:
            print(f"  ⚠️ RAW save error for camera {camera_id}: {e}")
            gui_logger.error("[CAPTURE] RAW error saving camera %d: %s", camera_id, e)
    
    def _toggle_gallery(self):
        """Toggle gallery visibility using splitter"""
        if self.toggle_gallery_btn.isChecked():
            # Show gallery - restore size
            self.gallery.show()
            sizes = self.splitter.sizes()
            total = sum(sizes)
            self.splitter.setSizes([int(total * 0.7), int(total * 0.3)])
            gui_logger.info("[GALLERY] Shown - splitter sizes: %s", self.splitter.sizes())
        else:
            # Hide gallery - give all space to cameras
            self.gallery.hide()
            gui_logger.info("[GALLERY] Hidden")
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts - matches Tkinter behavior"""
        key = event.key()
        
        # Space or C: Capture All
        if key == Qt.Key.Key_Space or key == Qt.Key.Key_C:
            self._on_capture_all()
        
        # R: Restart all streams
        elif key == Qt.Key.Key_R:
            self._restart_all_streams()
        
        # S: Open settings
        elif key == Qt.Key.Key_S:
            self._open_settings()
        
        # G: Toggle gallery
        elif key == Qt.Key.Key_G:
            self.toggle_gallery_btn.click()
        
        # Escape: Show all cameras (exit exclusive mode)
        elif key == Qt.Key.Key_Escape:
            self._show_all_cameras()
        
        # Q: Quit
        elif key == Qt.Key.Key_Q:
            self.close()
        
        # Keys 1-8: Toggle camera preview (exclusive mode)
        elif key >= Qt.Key.Key_1 and key <= Qt.Key.Key_8:
            camera_id = key - Qt.Key.Key_1 + 1  # Convert to 1-8
            self._toggle_camera_preview(camera_id)
    
    def _on_capture_single(self, camera_id: int):
        """Capture single camera by ID (1-8)"""
        from config import SLAVES, get_slave_ports
        
        # Map camera_id to slave name and IP
        slave_names = ["rep1", "rep2", "rep3", "rep4", "rep5", "rep6", "rep7", "rep8"]
        if camera_id < 1 or camera_id > 8:
            return
        
        slave_name = slave_names[camera_id - 1]
        if slave_name in SLAVES:
            ip = SLAVES[slave_name]["ip"]
            print(f"\n📷 Capturing camera {camera_id} ({slave_name} @ {ip})...")
            self.network_manager.send_capture_command(ip, camera_id)
            self.capture_count += 1
            self._save_frame_capture(camera_id)
            self.status_bar.showMessage(f"Captured camera {camera_id}", 2000)
    
    def _toggle_camera_preview(self, camera_id: int):
        """Toggle exclusive camera preview - show only selected camera enlarged
        
        Matches Tkinter behavior:
        - If clicking the same camera that's already exclusive, return to normal view
        - Otherwise, enter exclusive mode showing only that camera enlarged
        
        In exclusive mode:
        - Requests higher resolution from camera for focus checking
        - Uses proper aspect ratio scaling (no distortion)
        """
        if camera_id < 1 or camera_id > 8:
            return
        
        # DEBOUNCE: Prevent rapid switching (300ms cooldown)
        current_time = time.time()
        if current_time - self._last_exclusive_switch < 0.3:
            return  # Ignore rapid keypresses
        self._last_exclusive_switch = current_time
        
        if self.exclusive_camera == camera_id:
            # Already showing this camera exclusively - return to normal view
            print(f"🔲 Exiting exclusive mode for camera {camera_id}")
            gui_logger.info("[EXCLUSIVE] Exiting exclusive mode for camera %d", camera_id)
            self._show_all_cameras()
        else:
            # Enter exclusive mode for this camera
            print(f"🔳 Entering exclusive mode for camera {camera_id}")
            gui_logger.info("[EXCLUSIVE] Entering exclusive mode for camera %d", camera_id)
            self.exclusive_camera = camera_id
            
            # Request higher resolution for focus checking
            if ENABLE_RESOLUTION_SWITCHING:
                widget = self.camera_widgets[camera_id - 1]
                print(f"📐 Requesting HD resolution ({EXCLUSIVE_RESOLUTION[0]}x{EXCLUSIVE_RESOLUTION[1]}) for camera {camera_id}")
                gui_logger.info("[RESOLUTION] Requesting %dx%d for camera %d (ip=%s)", 
                              EXCLUSIVE_RESOLUTION[0], EXCLUSIVE_RESOLUTION[1], camera_id, widget.ip)
                self.network_manager.send_set_resolution(
                    widget.ip, 
                    EXCLUSIVE_RESOLUTION[0], 
                    EXCLUSIVE_RESOLUTION[1], 
                    camera_id
                )
                self._hd_cameras.add(camera_id)  # Track for reset later
            
            # Configure all widgets for exclusive/normal mode
            for i, widget in enumerate(self.camera_widgets):
                widget_camera_id = i + 1
                if widget_camera_id == camera_id:
                    # Enable exclusive mode for selected camera (proper aspect ratio scaling)
                    widget.set_exclusive_mode(True)
                    widget.show()
                    # Remove from current position and re-add spanning multiple cells
                    self.camera_grid.removeWidget(widget)
                    self.camera_grid.addWidget(widget, 0, 0, 2, 4)  # row, col, rowspan, colspan
                else:
                    # Disable exclusive mode and hide other cameras
                    widget.set_exclusive_mode(False)
                    widget.hide()
            
            # Force redraw after layout processes (100ms delay)
            QTimer.singleShot(100, lambda: self._force_redraw_camera(camera_id))
            
            self.status_bar.showMessage(f"Camera {camera_id} - Focus Check Mode (Escape to exit)", 3000)
    
    def _show_all_cameras(self):
        """Return to normal view showing all 8 cameras in 2x4 grid
        
        Called when:
        - Escape key pressed
        - Same camera number pressed again in exclusive mode
        """
        if self.exclusive_camera is None:
            return  # Already in normal view
        
        print("🔲 Showing all cameras in normal grid")
        gui_logger.info("[EXCLUSIVE] Returning to normal grid view")
        
        # Reset resolution for ALL cameras that were set to HD (not just current one!)
        if ENABLE_RESOLUTION_SWITCHING and self._hd_cameras:
            print(f"📐 Resetting {len(self._hd_cameras)} cameras to normal resolution ({NORMAL_RESOLUTION[0]}x{NORMAL_RESOLUTION[1]})")
            gui_logger.info("[RESOLUTION] Resetting %d cameras to %dx%d: %s", 
                          len(self._hd_cameras), NORMAL_RESOLUTION[0], NORMAL_RESOLUTION[1], list(self._hd_cameras))
            for camera_id in self._hd_cameras:
                widget = self.camera_widgets[camera_id - 1]
                self.network_manager.send_set_resolution(
                    widget.ip,
                    NORMAL_RESOLUTION[0],
                    NORMAL_RESOLUTION[1],
                    camera_id
                )
            self._hd_cameras.clear()  # All reset, clear tracking
        
        self.exclusive_camera = None
        
        # Restore all cameras to their normal grid positions (2x4)
        for i, widget in enumerate(self.camera_widgets):
            # Disable exclusive mode (return to normal fast scaling)
            widget.set_exclusive_mode(False)
            # Remove from current position first
            self.camera_grid.removeWidget(widget)
            # Re-add at normal position: row = i // 4, col = i % 4
            self.camera_grid.addWidget(widget, i // 4, i % 4)
            widget.show()
        
        # Check gallery state after returning to grid
        gallery_visible = self.gallery.isVisible() if hasattr(self, 'gallery') else False
        gui_logger.info("[GRID] Restored 8-camera grid, gallery visible: %s", gallery_visible)
        
        # Force redraw all cameras after layout processes (100ms delay)
        QTimer.singleShot(100, self._force_redraw_all_cameras)
        
        self.status_bar.showMessage("All cameras", 2000)
    
    def _force_redraw_camera(self, camera_id: int):
        """Force redraw a specific camera with current frame at new size"""
        if camera_id in self.decoded_frames:
            widget = self.camera_widgets[camera_id - 1]
            widget.update_frame(self.decoded_frames[camera_id])
    
    def _force_redraw_all_cameras(self):
        """Force redraw all cameras with current frames at new sizes"""
        for camera_id, pixmap in self.decoded_frames.items():
            widget = self.camera_widgets[camera_id - 1]
            widget.update_frame(pixmap)
    
    def _restart_all_streams(self):
        """Restart video streams on all cameras
        
        Stops all streams, waits briefly, then starts them again.
        Useful when streams get out of sync or stop responding.
        """
        print("\n🔄 Restarting all video streams...")
        self.status_bar.showMessage("Restarting streams...", 2000)
        
        # Stop all streams
        self.network_manager.send_stop_all_streams()
        
        # Start streams again after a short delay
        QTimer.singleShot(1000, self._start_all_streams)
        
        # Update status after restart completes
        QTimer.singleShot(2000, lambda: self.status_bar.showMessage("Streams restarted", 2000))
    
    def _open_settings(self):
        """Open camera settings dialog for all cameras
        
        Opens the settings dialog to adjust camera parameters
        """
        print("\n⚙️ Opening settings dialog...")
        
        # Use camera 1 as default for the settings dialog
        # The dialog can affect all cameras or specific ones
        if self.camera_widgets:
            first_camera = self.camera_widgets[0]
            self._on_camera_settings(first_camera.camera_id, first_camera.ip)
    
    def closeEvent(self, event):
        """Cleanup"""
        self.timer.stop()
        self.gallery.cleanup()
        self.network_manager.shutdown()
        
        elapsed = time.time() - self.start_time
        gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*70)
        print("SESSION COMPLETE")
        print("="*70)
        print(f"Frames: {self.frame_count} | Time: {elapsed:.1f}s | FPS: {gui_fps:.1f}")
        print(f"Captures: {self.capture_count}")
        print("="*70)
        
        event.accept()


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: white;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
