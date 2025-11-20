#!/usr/bin/env python3
"""
8-Camera Grid Display with Capture - PySide6 Implementation
GERTIE Phase 3: Feature Migration - Still Capture

Features:
- 2x4 grid layout (8 cameras)
- Real-time frame updates using QTimer
- Capture button per camera
- Mock capture: saves current frame to disk
- Network manager integration
- Status feedback
"""

import sys
import os
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, 
    QLabel, QVBoxLayout, QHBoxLayout, QStatusBar, QPushButton
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PIL.ImageQt import ImageQt

# Import mock camera system and network manager
from mock_camera import MockCameraSystem
from network_manager import NetworkManager


class CameraWidget(QWidget):
    """Widget representing a single camera with video feed and controls"""
    
    capture_requested = Signal(int, str)  # camera_id, ip
    
    def __init__(self, camera_id: int, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.ip = f"192.168.0.{200 + camera_id}"  # Mock IPs
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                background-color: #000;
                min-width: 320px;
                min-height: 240px;
            }
        """)
        self.video_label.setScaledContents(True)
        layout.addWidget(self.video_label)
        
        # Control panel
        controls = QHBoxLayout()
        controls.setSpacing(5)
        
        # Camera label
        cam_label = QLabel(f"REP{self.camera_id}")
        cam_label.setStyleSheet("color: white; font-weight: bold;")
        controls.addWidget(cam_label)
        
        controls.addStretch()
        
        # Capture button
        self.capture_btn = QPushButton("📷 Capture")
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b6;
            }
            QPushButton:pressed {
                background-color: #194;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
        """)
        self.capture_btn.clicked.connect(self._on_capture)
        controls.addWidget(self.capture_btn)
        
        layout.addLayout(controls)
    
    def _on_capture(self):
        """Handle capture button click"""
        self.capture_requested.emit(self.camera_id, self.ip)
    
    def update_frame(self, pixmap: QPixmap):
        """Update video frame"""
        self.video_label.setPixmap(pixmap)
    
    def set_capture_enabled(self, enabled: bool):
        """Enable or disable capture button"""
        self.capture_btn.setEnabled(enabled)


class CameraGridWindow(QMainWindow):
    """Main window displaying 8-camera grid with capture functionality"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GERTIE Qt - Phase 3: Still Capture")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize mock camera system
        self.camera_system = MockCameraSystem(resolution=(640, 480), fps=30)
        
        # Initialize network manager
        self.network_manager = NetworkManager(mock_mode=True)
        self.network_manager.capture_completed.connect(self._on_capture_completed)
        self.network_manager.capture_failed.connect(self._on_capture_failed)
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.paused = False
        
        # Capture tracking
        self.captures_dir = "mock_captures"
        os.makedirs(self.captures_dir, exist_ok=True)
        self.capture_count = 0
        
        # Setup UI
        self._setup_ui()
        
        # Setup update timer (30 FPS target)
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frames)
        self.timer.start(33)  # ~30 FPS
        
        print("="*60)
        print("GERTIE Qt - Phase 3: Still Capture")
        print("="*60)
        print("Controls:")
        print("  Space: Pause/Resume")
        print("  R: Reset stats")
        print("  C: Capture all cameras")
        print("  Q: Quit")
        print(f"  Captures saved to: {self.captures_dir}/")
        print("="*60)
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QVBoxLayout()
        central.setLayout(main_layout)
        
        # Grid layout for cameras (2 rows x 4 columns)
        grid = QGridLayout()
        grid.setSpacing(5)
        
        # Create 8 camera widgets
        self.camera_widgets = []
        for i in range(8):
            widget = CameraWidget(i + 1)
            widget.capture_requested.connect(self._on_camera_capture)
            
            row = i // 4
            col = i % 4
            grid.addWidget(widget, row, col)
            self.camera_widgets.append(widget)
        
        main_layout.addLayout(grid)
        
        # Bottom control panel
        bottom_controls = QHBoxLayout()
        
        # Capture all button
        capture_all_btn = QPushButton("📷 Capture All")
        capture_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #25a;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #36b;
            }
            QPushButton:pressed {
                background-color: #149;
            }
        """)
        capture_all_btn.clicked.connect(self._on_capture_all)
        bottom_controls.addStretch()
        bottom_controls.addWidget(capture_all_btn)
        bottom_controls.addStretch()
        
        main_layout.addLayout(bottom_controls)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Initializing...")
    
    def _update_frames(self):
        """Update all camera frames (called by timer)"""
        if self.paused:
            return
        
        # Generate frames from mock cameras
        frames = self.camera_system.generate_all_frames()
        
        # Store current frames for capture
        self.current_frames = frames
        
        # Update each widget with new frame
        for widget, frame in zip(self.camera_widgets, frames):
            # Convert PIL Image to QPixmap
            qimage = ImageQt(frame)
            pixmap = QPixmap.fromImage(qimage)
            widget.update_frame(pixmap)
        
        # Update stats
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        
        # Update status bar every 30 frames
        if self.frame_count % 30 == 0:
            gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
            system_fps = self.camera_system.get_system_fps()
            self.status_bar.showMessage(
                f"GUI FPS: {gui_fps:.1f} | System FPS: {system_fps:.1f} | "
                f"Frames: {self.frame_count} | Captures: {self.capture_count}"
            )
    
    def _on_camera_capture(self, camera_id: int, ip: str):
        """Handle individual camera capture"""
        print(f"\n📷 Capture requested: Camera {camera_id} ({ip})")
        
        # Send network command (mock)
        self.network_manager.send_capture_command(ip, camera_id)
        
        # Save current frame (mock capture)
        self._save_mock_capture(camera_id)
    
    def _on_capture_all(self):
        """Handle capture all cameras"""
        print(f"\n📷 Capture ALL requested")
        
        # Capture from all cameras
        for i in range(8):
            camera_id = i + 1
            ip = f"192.168.0.{200 + camera_id}"
            
            # Send network command
            self.network_manager.send_capture_command(ip, camera_id)
            
            # Save frame
            self._save_mock_capture(camera_id)
    
    def _save_mock_capture(self, camera_id: int):
        """Save current frame as mock capture"""
        try:
            frame_index = camera_id - 1
            if frame_index < len(self.current_frames):
                frame = self.current_frames[frame_index]
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"{self.captures_dir}/rep{camera_id}_{timestamp}.jpg"
                
                # Save frame
                frame.save(filename, quality=95)
                
                self.capture_count += 1
                print(f"  ✓ Saved: {filename}")
                
                # Update status
                self.status_bar.showMessage(
                    f"✓ Captured camera {camera_id} - Total captures: {self.capture_count}",
                    3000  # Show for 3 seconds
                )
        except Exception as e:
            print(f"  ✗ Error saving capture: {e}")
    
    def _on_capture_completed(self, ip: str):
        """Handle capture completion from network"""
        print(f"  ✓ Network: Capture completed for {ip}")
    
    def _on_capture_failed(self, ip: str, error: str):
        """Handle capture failure from network"""
        print(f"  ✗ Network: Capture failed for {ip}: {error}")
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        key = event.key()
        
        if key == Qt.Key.Key_Space:
            # Toggle pause
            self.paused = not self.paused
            status = "PAUSED" if self.paused else "RUNNING"
            self.status_bar.showMessage(f"Status: {status}")
            print(f"Playback {status}")
        
        elif key == Qt.Key.Key_R:
            # Reset stats
            self.frame_count = 0
            self.start_time = time.time()
            self.camera_system.reset_all_stats()
            self.status_bar.showMessage("Stats reset")
            print("Stats reset")
        
        elif key == Qt.Key.Key_C:
            # Capture all
            self._on_capture_all()
        
        elif key == Qt.Key.Key_Q:
            # Quit
            print("Quitting...")
            self.close()
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        self.network_manager.shutdown()
        
        # Print final stats
        elapsed = time.time() - self.start_time
        gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        print(f"Total Frames: {self.frame_count}")
        print(f"Total Time: {elapsed:.2f}s")
        print(f"Average GUI FPS: {gui_fps:.1f}")
        print(f"Total Captures: {self.capture_count}")
        print(f"Captures saved to: {self.captures_dir}/")
        print("="*60)
        
        event.accept()


def main():
    """Main entry point"""
    print("="*60)
    print("GERTIE Qt Camera Grid - Phase 3")
    print("Testing Still Capture with Mock Cameras")
    print("="*60)
    
    app = QApplication(sys.argv)
    window = CameraGridWindow()
    window.show()
    
    exit_code = app.exec()
    print(f"\nApplication exited with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())