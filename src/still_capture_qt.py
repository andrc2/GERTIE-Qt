#!/usr/bin/env python3
"""
GERTIE Qt - Still Capture Mode (Phase 3)
Simple single-camera capture with mock camera support
Features: View feed, capture on space bar, save with timestamp
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QStatusBar
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QImage, QKeySequence, QShortcut

# Import our mock camera
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_camera import MockCamera


class StillCaptureWindow(QMainWindow):
    """Main window for still capture mode"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GERTIE Still Capture - Qt Version")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize camera system
        self.cameras = {}
        self.current_camera_id = "REP1"
        self.capture_count = 0
        
        # Create save directory
        self.save_dir = Path.home() / "Desktop" / "gertie_captures"
        self.save_dir.mkdir(exist_ok=True)
        
        # Setup UI
        self.setup_ui()
        
        # Initialize cameras
        self.init_cameras()
        
        # Start display timer
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(33)  # ~30 FPS
        
        self.update_status("Ready - Press SPACE to capture")
    
    def setup_ui(self):
        """Create the user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Top control bar
        controls = QHBoxLayout()
        
        # Camera selector
        controls.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self.camera_combo.addItems([f"REP{i}" for i in range(1, 9)])
        self.camera_combo.currentTextChanged.connect(self.change_camera)
        controls.addWidget(self.camera_combo)
        
        controls.addStretch()
        
        # Capture button
        self.capture_btn = QPushButton("📷 Capture (SPACE)")
        self.capture_btn.clicked.connect(self.capture_image)
        self.capture_btn.setMinimumWidth(150)
        controls.addWidget(self.capture_btn)
        
        layout.addLayout(controls)
        
        # Camera display
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setMinimumSize(640, 480)
        self.display_label.setStyleSheet("QLabel { background-color: black; }")
        layout.addWidget(self.display_label, stretch=1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Keyboard shortcuts
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.activated.connect(self.capture_image)
    
    def init_cameras(self):
        """Initialize all mock cameras"""
        patterns = ['color_bars', 'grid', 'noise', 'gradient', 'checkerboard']
        
        for i in range(1, 9):
            camera_id = f"REP{i}"
            pattern = patterns[i % len(patterns)]  # Cycle through patterns
            self.cameras[camera_id] = MockCamera(
                camera_id=i,  # MockCamera expects int, not string
                resolution=(640, 480),
                pattern=pattern,
                fps=30
            )
    
    def change_camera(self, camera_id):
        """Switch to different camera"""
        self.current_camera_id = camera_id
        self.update_status(f"Switched to {camera_id}")
    
    def update_display(self):
        """Update the camera display"""
        if self.current_camera_id not in self.cameras:
            return
        
        # Get frame from current camera
        camera = self.cameras[self.current_camera_id]
        pil_image = camera.get_frame()
        
        # Convert PIL Image to QPixmap
        img_data = pil_image.tobytes("raw", "RGB")
        qimage = QImage(
            img_data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 3,
            QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale to fit display while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.display_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.display_label.setPixmap(scaled_pixmap)
    
    def capture_image(self):
        """Capture and save current frame"""
        if self.current_camera_id not in self.cameras:
            self.update_status("❌ No camera selected")
            return
        
        # Get current frame
        camera = self.cameras[self.current_camera_id]
        pil_image = camera.get_frame()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.current_camera_id}_{timestamp}.png"
        filepath = self.save_dir / filename
        
        # Save image
        try:
            pil_image.save(str(filepath))
            self.capture_count += 1
            self.update_status(f"✅ Saved: {filename} (Total: {self.capture_count})")
        except Exception as e:
            self.update_status(f"❌ Error saving: {e}")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_bar.showMessage(message)
    
    def closeEvent(self, event):
        """Clean shutdown"""
        self.display_timer.stop()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = StillCaptureWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
