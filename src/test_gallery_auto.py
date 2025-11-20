#!/usr/bin/env python3
"""
Automated test for GERTIE Qt with Gallery
Fully hands-off validation:
1. Starts application
2. Triggers multiple captures automatically
3. Verifies gallery updates
4. Reports results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gertie_qt import MainWindow
import time


def run_automated_test():
    """Run fully automated gallery test"""
    print("="*70)
    print("GERTIE Qt - Automated Gallery + Capture Test")
    print("="*70)
    print("Test Plan:")
    print("  0s: Start application")
    print("  2s: Capture camera 1")
    print("  3s: Capture camera 2")
    print("  4s: Capture all cameras (8 more captures)")
    print("  6s: Verify gallery shows 10 total captures")
    print("  8s: Exit and report")
    print("="*70)
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Count initial captures
    initial_count = len([f for f in os.listdir(window.captures_dir) if f.endswith('.jpg')]) if os.path.exists(window.captures_dir) else 0
    print(f"\nInitial captures in directory: {initial_count}")
    
    # Test sequence
    test_results = {
        'captures_triggered': 0,
        'gallery_checked': False,
        'gallery_count': 0,
        'initial_count': initial_count,
        'expected_new': 10
    }
    
    def capture_cam1():
        print("\n[2s] Triggering capture: Camera 1")
        window._on_camera_capture(1, "192.168.0.201")
        test_results['captures_triggered'] += 1
    
    def capture_cam2():
        print("[3s] Triggering capture: Camera 2")
        window._on_camera_capture(2, "192.168.0.202")
        test_results['captures_triggered'] += 1
    
    def capture_all():
        print("[4s] Triggering capture: All cameras")
        window._on_capture_all()
        test_results['captures_triggered'] += 8
    
    def verify_gallery():
        print("\n[6s] Verifying gallery...")
        # Give gallery time to refresh
        QTimer.singleShot(500, check_gallery)
    
    def check_gallery():
        gallery_count = len(window.gallery.thumbnails)
        test_results['gallery_checked'] = True
        test_results['gallery_count'] = gallery_count
        expected_total = test_results['initial_count'] + test_results['expected_new']
        
        print(f"  Gallery shows: {gallery_count} images")
        print(f"  Expected: {expected_total} images (initial {test_results['initial_count']} + new {test_results['expected_new']})")
        
        if gallery_count == expected_total:
            print("  ✓ Gallery count CORRECT")
        else:
            print(f"  ✗ Gallery count INCORRECT (got {gallery_count}, expected {expected_total})")
    
    def finish_test():
        print("\n[8s] Test complete - closing application")
        app.quit()
    
    # Schedule test actions
    QTimer.singleShot(2000, capture_cam1)
    QTimer.singleShot(3000, capture_cam2)
    QTimer.singleShot(4000, capture_all)
    QTimer.singleShot(6000, verify_gallery)
    QTimer.singleShot(8000, finish_test)
    
    # Run
    start_time = time.time()
    exit_code = app.exec()
    elapsed = time.time() - start_time
    
    # Final report
    expected_total = test_results['initial_count'] + test_results['expected_new']
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"Duration: {elapsed:.1f}s")
    print(f"Initial Captures: {test_results['initial_count']}")
    print(f"New Captures Triggered: {test_results['captures_triggered']}")
    print(f"Gallery Verified: {'Yes' if test_results['gallery_checked'] else 'No'}")
    print(f"Gallery Count: {test_results['gallery_count']} / {expected_total}")
    
    # Determine pass/fail
    success = (
        test_results['gallery_checked'] and
        test_results['gallery_count'] == expected_total and
        test_results['captures_triggered'] == test_results['expected_new']
    )
    
    if success:
        print("\n✓ TEST PASSED - Gallery system working correctly!")
        print("  - All captures saved")
        print("  - Gallery auto-updated")
        print("  - Thumbnail count correct")
    else:
        print("\n✗ TEST FAILED")
        if not test_results['gallery_checked']:
            print("  - Gallery verification did not run")
        if test_results['gallery_count'] != expected_total:
            print(f"  - Gallery count mismatch: {test_results['gallery_count']} != {expected_total}")
    
    print("="*70)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_automated_test()
    sys.exit(exit_code)
