#!/usr/bin/env python3
"""
Qt Framework Performance Benchmark
Compares PyQt6 vs PySide6 for GERTIE camera system
"""

import sys
import time
import psutil
import os

def benchmark_pyqt6():
    """Benchmark PyQt6 performance"""
    print("\n=== PyQt6 Benchmark ===")
    
    # Measure import time
    start = time.time()
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QPixmap, QImage
    import_time = time.time() - start
    print(f"Import time: {import_time:.3f}s")
    
    # Measure memory before
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create application
    start = time.time()
    app = QApplication(sys.argv)
    app_time = time.time() - start
    print(f"QApplication creation: {app_time:.3f}s")
    
    # Create window with multiple widgets
    start = time.time()
    window = QMainWindow()
    window.setWindowTitle("PyQt6 Benchmark")
    window.setGeometry(100, 100, 800, 600)
    
    # Create 8 labels (simulating 8 camera feeds)
    central = QWidget()
    layout = QVBoxLayout()
    labels = []
    for i in range(8):
        label = QLabel(f"Camera {i+1}")
        label.setStyleSheet("border: 2px solid green; padding: 20px;")
        layout.addWidget(label)
        labels.append(label)
    
    central.setLayout(layout)
    window.setCentralWidget(central)
    window.show()
    widget_time = time.time() - start
    print(f"Widget creation (8 labels): {widget_time:.3f}s")
    
    # Measure memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_usage = mem_after - mem_before
    print(f"Memory usage: {mem_usage:.1f} MB")
    
    # Test update performance
    start = time.time()
    for _ in range(100):
        for i, label in enumerate(labels):
            label.setText(f"Camera {i+1} - Frame {_}")
        app.processEvents()
    update_time = time.time() - start
    fps_equiv = 100 / update_time
    print(f"100 updates of 8 widgets: {update_time:.3f}s ({fps_equiv:.1f} FPS equivalent)")
    
    # Close
    QTimer.singleShot(100, app.quit)
    app.exec()
    
    return {
        'import_time': import_time,
        'app_time': app_time,
        'widget_time': widget_time,
        'update_time': update_time,
        'fps_equiv': fps_equiv,
        'memory_mb': mem_usage,
        'total_time': import_time + app_time + widget_time
    }

def benchmark_pyside6():
    """Benchmark PySide6 performance"""
    print("\n=== PySide6 Benchmark ===")
    
    # Measure import time
    start = time.time()
    from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap, QImage
    import_time = time.time() - start
    print(f"Import time: {import_time:.3f}s")
    
    # Measure memory before
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create application
    start = time.time()
    app = QApplication(sys.argv)
    app_time = time.time() - start
    print(f"QApplication creation: {app_time:.3f}s")
    
    # Create window with multiple widgets
    start = time.time()
    window = QMainWindow()
    window.setWindowTitle("PySide6 Benchmark")
    window.setGeometry(100, 100, 800, 600)
    
    # Create 8 labels (simulating 8 camera feeds)
    central = QWidget()
    layout = QVBoxLayout()
    labels = []
    for i in range(8):
        label = QLabel(f"Camera {i+1}")
        label.setStyleSheet("border: 2px solid blue; padding: 20px;")
        layout.addWidget(label)
        labels.append(label)
    
    central.setLayout(layout)
    window.setCentralWidget(central)
    window.show()
    widget_time = time.time() - start
    print(f"Widget creation (8 labels): {widget_time:.3f}s")
    
    # Measure memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_usage = mem_after - mem_before
    print(f"Memory usage: {mem_usage:.1f} MB")
    
    # Test update performance
    start = time.time()
    for _ in range(100):
        for i, label in enumerate(labels):
            label.setText(f"Camera {i+1} - Frame {_}")
        app.processEvents()
    update_time = time.time() - start
    fps_equiv = 100 / update_time
    print(f"100 updates of 8 widgets: {update_time:.3f}s ({fps_equiv:.1f} FPS equivalent)")
    
    # Close
    QTimer.singleShot(100, app.quit)
    app.exec()
    
    return {
        'import_time': import_time,
        'app_time': app_time,
        'widget_time': widget_time,
        'update_time': update_time,
        'fps_equiv': fps_equiv,
        'memory_mb': mem_usage,
        'total_time': import_time + app_time + widget_time
    }

def compare_results(pyqt_results, pyside_results):
    """Compare and display results"""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON - PyQt6 vs PySide6")
    print("="*60)
    
    print(f"\n{'Metric':<30} {'PyQt6':<15} {'PySide6':<15} {'Winner'}")
    print("-" * 60)
    
    # Import time
    winner = "PyQt6" if pyqt_results['import_time'] < pyside_results['import_time'] else "PySide6"
    print(f"{'Import Time':<30} {pyqt_results['import_time']:>6.3f}s      {pyside_results['import_time']:>6.3f}s      {winner}")
    
    # App creation
    winner = "PyQt6" if pyqt_results['app_time'] < pyside_results['app_time'] else "PySide6"
    print(f"{'App Creation':<30} {pyqt_results['app_time']:>6.3f}s      {pyside_results['app_time']:>6.3f}s      {winner}")
    
    # Widget creation
    winner = "PyQt6" if pyqt_results['widget_time'] < pyside_results['widget_time'] else "PySide6"
    print(f"{'Widget Creation (8x)':<30} {pyqt_results['widget_time']:>6.3f}s      {pyside_results['widget_time']:>6.3f}s      {winner}")
    
    # Update performance (critical for camera feeds)
    winner = "PyQt6" if pyqt_results['update_time'] < pyside_results['update_time'] else "PySide6"
    print(f"{'Update Performance':<30} {pyqt_results['update_time']:>6.3f}s      {pyside_results['update_time']:>6.3f}s      {winner}")
    
    # FPS equivalent (higher is better)
    winner = "PyQt6" if pyqt_results['fps_equiv'] > pyside_results['fps_equiv'] else "PySide6"
    print(f"{'FPS Equivalent':<30} {pyqt_results['fps_equiv']:>6.1f} fps    {pyside_results['fps_equiv']:>6.1f} fps    {winner}")
    
    # Memory usage
    winner = "PyQt6" if pyqt_results['memory_mb'] < pyside_results['memory_mb'] else "PySide6"
    print(f"{'Memory Usage':<30} {pyqt_results['memory_mb']:>6.1f} MB     {pyside_results['memory_mb']:>6.1f} MB     {winner}")
    
    # Total startup time
    winner = "PyQt6" if pyqt_results['total_time'] < pyside_results['total_time'] else "PySide6"
    print(f"{'Total Startup Time':<30} {pyqt_results['total_time']:>6.3f}s      {pyside_results['total_time']:>6.3f}s      {winner}")
    
    print("\n" + "="*60)
    
    # Calculate overall winner
    pyqt_wins = 0
    pyside_wins = 0
    
    if pyqt_results['import_time'] < pyside_results['import_time']: pyqt_wins += 1
    else: pyside_wins += 1
    
    if pyqt_results['update_time'] < pyside_results['update_time']: pyqt_wins += 2  # Double weight for update
    else: pyside_wins += 2
    
    if pyqt_results['fps_equiv'] > pyside_results['fps_equiv']: pyqt_wins += 2  # Double weight for FPS
    else: pyside_wins += 2
    
    if pyqt_results['memory_mb'] < pyside_results['memory_mb']: pyqt_wins += 1
    else: pyside_wins += 1
    
    print(f"\nOVERALL RECOMMENDATION for GERTIE:")
    if pyqt_wins > pyside_wins:
        print(f"  ✓ PyQt6 (Score: {pyqt_wins} vs {pyside_wins})")
        print(f"  Reason: Better performance for camera feed updates")
    else:
        print(f"  ✓ PySide6 (Score: {pyside_wins} vs {pyqt_wins})")
        print(f"  Reason: Better performance for camera feed updates")
    
    print("\nKey considerations:")
    print(f"  - Update speed is critical for 8-camera video display")
    print(f"  - Target: 30 FPS for smooth video")
    print(f"  - Memory efficiency important for long-running system")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("GERTIE Qt Framework Performance Benchmark")
    print("Testing PyQt6 vs PySide6 for 8-camera system")
    print("="*60)
    
    # Run benchmarks
    pyqt_results = benchmark_pyqt6()
    time.sleep(1)  # Brief pause between tests
    pyside_results = benchmark_pyside6()
    
    # Compare
    compare_results(pyqt_results, pyside_results)
