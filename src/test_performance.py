#!/usr/bin/env python3
"""
PySide6 8-Camera Performance Validation
Automated test to validate 30 FPS target with 8 simultaneous camera feeds
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from camera_grid import CameraGridWindow


def run_performance_test(duration_seconds=10):
    """
    Run automated performance test
    
    Args:
        duration_seconds: How long to run the test
        
    Returns:
        dict with performance metrics
    """
    print("="*60)
    print("GERTIE Qt - Automated Performance Test")
    print("="*60)
    print(f"Test Duration: {duration_seconds} seconds")
    print(f"Target: 30 FPS with 8 cameras")
    print()
    
    app = QApplication(sys.argv)
    window = CameraGridWindow()
    window.show()
    
    # Auto-close after duration
    QTimer.singleShot(duration_seconds * 1000, app.quit)
    
    start_time = time.time()
    app.exec()
    elapsed = time.time() - start_time
    
    # Calculate metrics
    total_frames = window.frame_count
    gui_fps = total_frames / elapsed if elapsed > 0 else 0
    system_fps = window.camera_system.get_system_fps()
    
    results = {
        'total_frames': total_frames,
        'elapsed_time': elapsed,
        'gui_fps': gui_fps,
        'system_fps': system_fps,
        'target_fps': 30,
        'success': gui_fps >= 28,  # Allow 2 FPS tolerance
    }
    
    return results


def print_results(results):
    """Print test results"""
    print("\n" + "="*60)
    print("PERFORMANCE TEST RESULTS")
    print("="*60)
    print(f"Total Frames Generated: {results['total_frames']}")
    print(f"Test Duration: {results['elapsed_time']:.2f}s")
    print(f"GUI FPS: {results['gui_fps']:.1f}")
    print(f"System FPS: {results['system_fps']:.1f}")
    print(f"Target FPS: {results['target_fps']}")
    print()
    
    if results['success']:
        print("✓ TEST PASSED - Meets 30 FPS target!")
        print(f"  Achieved {results['gui_fps']:.1f} FPS (target: 30 FPS)")
    else:
        print("✗ TEST FAILED - Below 30 FPS target")
        print(f"  Achieved {results['gui_fps']:.1f} FPS (target: 30 FPS)")
    
    print("="*60)
    
    # Additional analysis
    print("\nPERFORMANCE ANALYSIS:")
    print(f"  - Frame generation rate: {results['system_fps']:.1f} FPS")
    print(f"  - GUI update rate: {results['gui_fps']:.1f} FPS")
    print(f"  - Performance headroom: {(results['gui_fps'] / results['target_fps'] * 100):.0f}%")
    
    if results['gui_fps'] > 35:
        print("  - Excellent: Well above 30 FPS target")
    elif results['gui_fps'] >= 30:
        print("  - Good: Meeting 30 FPS target")
    elif results['gui_fps'] >= 25:
        print("  - Acceptable: Close to 30 FPS target")
    else:
        print("  - Poor: Below acceptable threshold")
    
    print("="*60)


if __name__ == "__main__":
    # Run 10-second test
    results = run_performance_test(duration_seconds=10)
    print_results(results)
    
    # Save results to file
    with open("../tests/performance_results.txt", "w") as f:
        f.write("GERTIE Qt - Phase 2 Performance Test Results\n")
        f.write("="*60 + "\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Frames: {results['total_frames']}\n")
        f.write(f"Duration: {results['elapsed_time']:.2f}s\n")
        f.write(f"GUI FPS: {results['gui_fps']:.1f}\n")
        f.write(f"System FPS: {results['system_fps']:.1f}\n")
        f.write(f"Target: {results['target_fps']} FPS\n")
        f.write(f"Result: {'PASS' if results['success'] else 'FAIL'}\n")
    
    print("\n✓ Results saved to tests/performance_results.txt")
    
    sys.exit(0 if results['success'] else 1)
