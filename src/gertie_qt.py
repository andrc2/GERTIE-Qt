#!/usr/bin/env python3
"""
GERTIE Qt - Complete Camera System with Gallery
Phase 3: Still Capture + Gallery Integration

Features:
- 8-camera grid display
- Still capture functionality
- Gallery panel with auto-refresh
- Integrated layout with toggle
"""

import sys
import os
import time
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


class CameraWidget(QWidget):
    """Widget representing a single camera with video feed and controls"""
    
    capture_requested = Signal(int, str)
    
    def __init__(self, camera_id: int, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.ip = f"192.168.0.{200 + camera_id}"
        
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
        
        layout.addLayout(controls)
    
    def _on_capture(self):
        self.capture_requested.emit(self.camera_id, self.ip)
    
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
        print("GERTIE Qt - Phase 3 Complete: Capture + Gallery")
        print("="*70)
        print("Controls:")
        print("  Space: Pause/Resume")
        print("  C: Capture all cameras")
        print("  G: Toggle gallery")
        print("  R: Reset stats")
        print("  Q: Quit")
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
        self.gallery = GalleryPanel(self.captures_dir)
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
        
        frames = self.camera_system.generate_all_frames()
        self.current_frames = frames
        
        for widget, frame in zip(self.camera_widgets, frames):
            qimage = ImageQt(frame)
            pixmap = QPixmap.fromImage(qimage)
            widget.update_frame(pixmap)
        
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
    
    def _on_capture_all(self):
        """Handle capture all"""
        print("\n📷 Capturing all cameras...")
        for i in range(8):
            camera_id = i + 1
            ip = f"192.168.0.{200 + camera_id}"
            self.network_manager.send_capture_command(ip, camera_id)
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
    
    def _toggle_gallery(self):
        """Toggle gallery visibility"""
        self.gallery.setVisible(self.toggle_gallery_btn.isChecked())
    
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
        
        elif key == Qt.Key.Key_Q:
            self.close()
    
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
