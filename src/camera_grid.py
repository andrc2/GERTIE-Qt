#!/usr/bin/env python3
"""
8-Camera Grid Display - PySide6 Implementation
First Qt GUI for GERTIE - displays 8 mock camera feeds in grid layout

Features:
- 2x4 grid layout (8 cameras)
- Real-time frame updates using QTimer
- QLabel with QPixmap for efficient display
- FPS monitoring and display
- Keyboard controls (Space to pause, Q to quit, R to reset stats)
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, 
    QLabel, QVBoxLayout, QHBoxLayout, QStatusBar
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QImage
import time
from PIL.ImageQt import ImageQt

# Import mock camera system
from mock_camera import MockCameraSystem


class CameraLabel(QLabel):
    """Custom QLabel for displaying camera feed"""
    
    def __init__(self, camera_id: int):
        super().__init__()
        self.camera_id = camera_id
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                background-color: #000;
                min-width: 320px;
                min-height: 240px;
            }
        """)
        self.setScaledContents(True)


class CameraGridWindow(QMainWindow):
    """Main window displaying 8-camera grid"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GERTIE Qt - 8 Camera Grid (Mock Data)")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize mock camera system
        self.camera_system = MockCameraSystem(resolution=(640, 480), fps=30)
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.paused = False
        
        # Setup UI
        self._setup_ui()
        
        # Setup update timer (30 FPS target)
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frames)
        self.timer.start(33)  # ~30 FPS (1000ms / 30 = 33ms)
        
        print("Camera Grid Window initialized")
        print("Controls:")
        print("  Space: Pause/Resume")
        print("  R: Reset stats")
        print("  Q: Quit")
    
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
        
        # Create 8 camera labels
        self.camera_labels = []
        for i in range(8):
            label = CameraLabel(i + 1)
            row = i // 4
            col = i % 4
            grid.addWidget(label, row, col)
            self.camera_labels.append(label)
        
        main_layout.addLayout(grid)
        
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
        
        # Update each label with new frame
        for i, (label, frame) in enumerate(zip(self.camera_labels, frames)):
            # Convert PIL Image to QPixmap
            qimage = ImageQt(frame)
            pixmap = QPixmap.fromImage(qimage)
            label.setPixmap(pixmap)
        
        # Update stats
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        
        # Update status bar every 30 frames
        if self.frame_count % 30 == 0:
            gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
            system_fps = self.camera_system.get_system_fps()
            self.status_bar.showMessage(
                f"GUI FPS: {gui_fps:.1f} | System FPS: {system_fps:.1f} | "
                f"Frames: {self.frame_count} | Elapsed: {elapsed:.1f}s"
            )
    
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
        
        elif key == Qt.Key.Key_Q:
            # Quit
            print("Quitting...")
            self.close()
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        
        # Print final stats
        elapsed = time.time() - self.start_time
        gui_fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        print(f"Total Frames: {self.frame_count}")
        print(f"Total Time: {elapsed:.2f}s")
        print(f"Average GUI FPS: {gui_fps:.1f}")
        print(f"Average System FPS: {self.camera_system.get_system_fps():.1f}")
        print("="*60)
        
        event.accept()



def main():
    """Main entry point"""
    print("="*60)
    print("GERTIE Qt Camera Grid - Phase 2")
    print("Testing PySide6 with Mock 8-Camera System")
    print("="*60)
    
    app = QApplication(sys.argv)
    window = CameraGridWindow()
    window.show()
    
    print("\nWindow displayed - starting video feed...")
    print("Press Space to pause/resume")
    print("Press R to reset statistics")
    print("Press Q to quit")
    print()
    
    exit_code = app.exec()
    print(f"\nApplication exited with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
