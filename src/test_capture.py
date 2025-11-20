#!/usr/bin/env python3
"""
Quick test of camera_grid_with_capture.py
Runs for 5 seconds, triggers one capture, then exits
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from camera_grid_with_capture import CameraGridWindow


def main():
    print("Testing camera grid with capture...")
    print("Will run for 5 seconds and trigger test capture")
    
    app = QApplication(sys.argv)
    window = CameraGridWindow()
    window.show()
    
    # Trigger capture after 2 seconds
    def test_capture():
        print("\n🧪 Test: Triggering capture on camera 1")
        window._on_camera_capture(1, "192.168.0.201")
    
    QTimer.singleShot(2000, test_capture)
    
    # Close after 5 seconds
    QTimer.singleShot(5000, app.quit)
    
    exit_code = app.exec()
    
    # Check results
    captures_dir = window.captures_dir
    if os.path.exists(captures_dir):
        files = os.listdir(captures_dir)
        print(f"\n✓ Test complete - {len(files)} capture(s) saved to {captures_dir}/")
        for f in files:
            print(f"  - {f}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())