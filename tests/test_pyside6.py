#!/usr/bin/env python3
"""
PySide6 Verification Test
Tests basic PySide6 functionality and import
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt, QTimer
import time

def test_pyside6_basic():
    """Test basic PySide6 window creation"""
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("PySide6 Test - GERTIE")
    window.setGeometry(100, 100, 400, 200)
    
    label = QLabel("PySide6 Working! ✓", window)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet("font-size: 24px; color: blue;")
    window.setCentralWidget(label)
    
    window.show()
    
    # Auto-close after 2 seconds
    QTimer.singleShot(2000, app.quit)
    
    return app.exec()

if __name__ == "__main__":
    print("Testing PySide6...")
    start_time = time.time()
    
    try:
        result = test_pyside6_basic()
        elapsed = time.time() - start_time
        print(f"✓ PySide6 test PASSED (window displayed for 2s)")
        print(f"  Import time: {elapsed:.3f}s")
        print(f"  Exit code: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ PySide6 test FAILED: {e}")
        sys.exit(1)
