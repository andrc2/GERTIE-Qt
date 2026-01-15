#!/usr/bin/env python3
"""
GERTIE Qt - Complete Camera System with Gallery
Phase 3: Still Capture + Gallery Integration + Network Commands

Features:
- 8-camera grid display
- Still capture functionality
- Gallery panel with auto-refresh
- Integrated layout with toggle
- Complete network command support
- Mock/Real network mode toggle
"""

import sys
import os
import time
import logging
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, 
    QLabel, QVBoxLayout, QHBoxLayout, QStatusBar, 
    QPushButton, QSplitter
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PIL.ImageQt import ImageQt

# Import our modules
from mock_camera import MockCameraSystem
from network_manager import NetworkManager
from gallery_panel import GalleryPanel
from camera_settings_dialog import CameraSettingsDialog
from config import get_ip_from_camera_id, SLAVES


class CameraWidget(QWidget):
    """Widget representing a single camera with video feed and controls"""
    
    capture_requested = Signal(int, str)
    settings_requested = Signal(int, str)  # camera_id, ip
    
    def __init__(self, camera_id: int, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.ip = get_ip_from_camera_id(camera_id)  # Use config for correct IP
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                background-color: #000;
                min-width: 280px;
                min-height: 210px;
            }
        """)
        self.video_label.setScaledContents(True)
        layout.addWidget(self.video_label)
        
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
        self.capture_requested.emit(self.camera_id, self.ip)
    
    def _on_settings(self):
        self.settings_requested.emit(self.camera_id, self.ip)
    
    def update_frame(self, pixmap: QPixmap):
        self.video_label.setPixmap(pixmap)


class MainWindow(QMainWindow):
    """Main window with camera grid and gallery"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GERTIE Qt - Phase 3: Capture + Gallery")
        self.setGeometry(50, 50, 1600, 900)
        
        # Initialize systems
        self.camera_system = MockCameraSystem(resolution=(640, 480), fps=30)
        self.network_manager = NetworkManager(mock_mode=True)
        self.network_manager.capture_completed.connect(self._on_capture_completed)
        self.network_manager.video_frame_received.connect(self._on_video_frame_received)
        self.network_manager.still_image_received.connect(self._on_still_image_received)
        
        # Real video frame buffers (camera_id -> latest frame)
        self.real_frames = {}
        
        # High-res captures directory
        self.hires_captures_dir = "hires_captures"
        os.makedirs(self.hires_captures_dir, exist_ok=True)
        
        # State
        self.frame_count = 0
        self.start_time = time.time()
        self.paused = False
        self.captures_dir = "mock_captures"
        os.makedirs(self.captures_dir, exist_ok=True)
        self.capture_count = 0
        self.current_frames = []
        
        # UI
        self._setup_ui()
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frames)
        self.timer.start(33)
        
        print("="*70)
        print("GERTIE Qt - Phase 3: Capture + Gallery + Network")
        print("="*70)
        print("Controls:")
        print("  Space: Pause/Resume video")
        print("  C: Capture all cameras")
        print("  G: Toggle gallery")
        print("  M: Toggle Mock/Real network mode")
        print("  R: Reset stats")
        print("  Q: Quit")
        print("  ⚙️ button: Per-camera settings")
        print("")
        print("Network Mode:")
        print("  🔧 MOCK MODE: Simulates commands (no Pi required)")
        print("  📡 REAL NETWORK: Sends UDP to Pi cameras")
        print("="*70)
    
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
        grid = QGridLayout()
        grid.setSpacing(5)
        
        self.camera_widgets = []
        for i in range(8):
            widget = CameraWidget(i + 1)
            widget.capture_requested.connect(self._on_camera_capture)
            widget.settings_requested.connect(self._on_camera_settings)
            grid.addWidget(widget, i // 4, i % 4)
            self.camera_widgets.append(widget)
        
        cameras_layout.addLayout(grid)
        
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
        
        # Network mode toggle button
        self.network_mode_btn = QPushButton("🔧 MOCK MODE")
        self.network_mode_btn.setCheckable(True)
        self.network_mode_btn.setChecked(True)  # Start in mock mode
        self.network_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #a52;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:checked {
                background-color: #a52;
            }
            QPushButton:!checked {
                background-color: #2a5;
            }
            QPushButton:hover { opacity: 0.9; }
        """)
        self.network_mode_btn.clicked.connect(self._toggle_network_mode)
        controls.addWidget(self.network_mode_btn)
        
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
        
        cameras_layout.addLayout(controls)
        
        # Right side - Gallery
        self.gallery = GalleryPanel(self.hires_captures_dir)
        self.gallery.setMinimumWidth(300)
        
        # Add to splitter
        self.splitter.addWidget(cameras_widget)
        self.splitter.addWidget(self.gallery)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _update_frames(self):
        """Update camera frames"""
        if self.paused:
            return
        
        # Check if using real or mock mode
        if self.network_manager.is_mock_mode():
            # Use mock frames
            frames = self.camera_system.generate_all_frames()
            self.current_frames = frames
            
            for widget, frame in zip(self.camera_widgets, frames):
                qimage = ImageQt(frame)
                pixmap = QPixmap.fromImage(qimage)
                widget.update_frame(pixmap)
        else:
            # Use real frames from network
            # Log real_frames status periodically
            if not hasattr(self, '_real_frame_log_count'):
                self._real_frame_log_count = 0
            self._real_frame_log_count += 1
            if self._real_frame_log_count == 1 or self._real_frame_log_count % 100 == 0:
                print(f"  🎬 Real mode update #{self._real_frame_log_count}: {len(self.real_frames)} cameras have frames: {list(self.real_frames.keys())}")
            
            for i, widget in enumerate(self.camera_widgets):
                camera_id = i + 1
                if camera_id in self.real_frames:
                    frame = self.real_frames[camera_id]
                    # Convert numpy array to PIL Image to QPixmap
                    from PIL import Image
                    pil_image = Image.fromarray(frame)
                    qimage = ImageQt(pil_image)
                    pixmap = QPixmap.fromImage(qimage)
                    widget.update_frame(pixmap)
                    # Store for capture
                    if len(self.current_frames) < 8:
                        self.current_frames = [None] * 8
                    self.current_frames[i] = pil_image
        
        self.frame_count += 1
        
        if self.frame_count % 30 == 0:
            elapsed = time.time() - self.start_time
            gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
            self.status_bar.showMessage(
                f"FPS: {gui_fps:.1f} | Frames: {self.frame_count} | Captures: {self.capture_count}"
            )
    
    def _on_camera_capture(self, camera_id: int, ip: str):
        """Handle single camera capture"""
        self.network_manager.send_capture_command(ip, camera_id)
        self._save_mock_capture(camera_id)
    
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
        """Handle capture all"""
        print("\n📷 Capturing all cameras...")
        # Use NetworkManager's batch function for correct IPs
        self.network_manager.send_capture_all()
        # Save mock captures locally
        for camera_id in range(1, 9):
            self._save_mock_capture(camera_id)
    
    def _save_mock_capture(self, camera_id: int):
        """Save current frame"""
        try:
            if camera_id - 1 < len(self.current_frames):
                frame = self.current_frames[camera_id - 1]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"{self.captures_dir}/rep{camera_id}_{timestamp}.jpg"
                frame.save(filename, quality=95)
                self.capture_count += 1
                print(f"  ✓ Saved: {filename}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    def _on_capture_completed(self, ip: str):
        """Network capture completed"""
        pass
    
    def _on_video_frame_received(self, ip: str, camera_id: int, data: bytes):
        """Handle incoming video frame from real camera"""
        try:
            import io
            from PIL import Image
            
            # Decode JPEG frame
            image = Image.open(io.BytesIO(data))
            
            # Convert to numpy array for display
            frame = np.array(image)
            
            # Store in buffer (keyed by camera_id)
            self.real_frames[camera_id] = frame
            
            # Log first frame per camera
            if not hasattr(self, '_frame_log_count'):
                self._frame_log_count = {}
            if camera_id not in self._frame_log_count:
                self._frame_log_count[camera_id] = 0
                print(f"  📹 First decoded frame from camera {camera_id}: {frame.shape}")
            self._frame_log_count[camera_id] += 1
            
        except Exception as e:
            print(f"  ⚠️ Frame decode error for camera {camera_id}: {e}")
    
    def _on_still_image_received(self, camera_id: int, data: bytes, timestamp: str):
        """Handle incoming high-resolution still image from real camera"""
        try:
            # Save to hires_captures directory
            filename = f"{self.hires_captures_dir}/rep{camera_id}_{timestamp}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(data)
            
            size_kb = len(data) / 1024
            self.capture_count += 1
            print(f"  📸 Hi-res saved: {filename} ({size_kb:.1f} KB)")
            
            # OPTIMIZED: Add to gallery immediately with image data (no polling delay)
            if hasattr(self, 'gallery') and self.gallery.isVisible():
                self.gallery.add_image_immediately(filename, data)
                
        except Exception as e:
            print(f"  ⚠️ Still save error for camera {camera_id}: {e}")
    
    def _toggle_gallery(self):
        """Toggle gallery visibility"""
        self.gallery.setVisible(self.toggle_gallery_btn.isChecked())
    
    def _toggle_network_mode(self):
        """Toggle between mock and real network mode"""
        mock_mode = self.network_mode_btn.isChecked()
        self.network_manager.set_mock_mode(mock_mode)
        
        if mock_mode:
            self.network_mode_btn.setText("🔧 MOCK MODE")
            self.network_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a52;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { opacity: 0.9; }
            """)
            print("\n🔧 Switched to MOCK MODE (no network traffic)")
            # Stop streams when going to mock mode
            self.network_manager.send_stop_all_streams()
        else:
            self.network_mode_btn.setText("📡 REAL NETWORK")
            self.network_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a5;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover { opacity: 0.9; }
            """)
            print("\n📡 Switched to REAL NETWORK MODE (commands sent to Pi cameras)")
            # Start streams on all cameras
            self.network_manager.send_start_all_streams()
            # Clear old frames
            self.real_frames = {}
    
    def keyPressEvent(self, event):
        """Handle keyboard"""
        key = event.key()
        
        if key == Qt.Key.Key_Space:
            self.paused = not self.paused
            status = "PAUSED" if self.paused else "RUNNING"
            self.status_bar.showMessage(f"Status: {status}", 2000)
        
        elif key == Qt.Key.Key_R:
            self.frame_count = 0
            self.start_time = time.time()
            self.camera_system.reset_all_stats()
            self.status_bar.showMessage("Stats reset", 2000)
        
        elif key == Qt.Key.Key_C:
            self._on_capture_all()
        
        elif key == Qt.Key.Key_G:
            self.toggle_gallery_btn.click()
        
        elif key == Qt.Key.Key_M:
            self.network_mode_btn.click()
        
        elif key == Qt.Key.Key_Q:
            self.close()
        
        # Keys 1-8: Capture individual cameras
        elif key >= Qt.Key.Key_1 and key <= Qt.Key.Key_8:
            camera_id = key - Qt.Key.Key_1 + 1  # Convert to 1-8
            self._on_capture_single(camera_id)
    
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
            self._save_mock_capture(camera_id)
            self.status_bar.showMessage(f"Captured camera {camera_id}", 2000)
    
    def closeEvent(self, event):
        """Cleanup"""
        self.timer.stop()
        self.gallery.stop_auto_refresh()
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
