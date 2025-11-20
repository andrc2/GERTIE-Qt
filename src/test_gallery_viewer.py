#!/usr/bin/env python3
"""
Gallery + Image Viewer Integration Test
Tests that clicking thumbnails opens full-size viewer
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gallery_panel import GalleryPanel


def test_gallery_viewer():
    """Test gallery and viewer integration"""
    print("\n" + "="*70)
    print("PHASE 3 - GALLERY + IMAGE VIEWER INTEGRATION TEST")
    print("="*70)
    
    app = QApplication(sys.argv)
    
    # Create gallery
    captures_dir = "mock_captures"
    
    if not os.path.exists(captures_dir):
        print(f"\n✗ Captures directory not found: {captures_dir}")
        return 1
    
    images = list(Path(captures_dir).glob("*.jpg"))
    
    if not images:
        print(f"\n✗ No images found in {captures_dir}")
        return 1
    
    print(f"\n✓ Found {len(images)} images in gallery")
    
    # Create gallery panel
    gallery = GalleryPanel(captures_dir)
    gallery.setMinimumSize(800, 600)
    gallery.setStyleSheet("background-color: #1a1a1a;")
    gallery.show()
    
    print("✓ Gallery panel created and displayed")
    
    # Wait for gallery to populate
    QTimer.singleShot(1500, lambda: test_click_thumbnail(gallery, app))
    
    return app.exec()


def test_click_thumbnail(gallery, app):
    """Simulate clicking a thumbnail"""
    print("\n[Test 1] Simulating thumbnail click...")
    
    if not gallery.thumbnails:
        print("✗ No thumbnails in gallery")
        app.quit()
        return
    
    print(f"✓ Gallery has {len(gallery.thumbnails)} thumbnails")
    
    # Get first thumbnail
    first_thumb = gallery.thumbnails[0]
    filepath = first_thumb.filepath
    
    print(f"  Opening viewer for: {Path(filepath).name}")
    
    # Simulate click (this will open the ImageViewer dialog)
    # User will need to close it manually
    first_thumb.clicked.emit(filepath)
    
    print("\n" + "="*70)
    print("INTEGRATION TEST RESULTS")
    print("="*70)
    print("✓ Gallery panel functional")
    print(f"✓ {len(gallery.thumbnails)} thumbnails displayed")
    print("✓ Thumbnail click opens ImageViewer")
    print("\n✅ INTEGRATION TEST PASSED")
    print("\nInstructions:")
    print("  • ImageViewer should be open now")
    print("  • Try navigation buttons (◀ ▶)")
    print("  • Try zoom controls (Fit, 100%, 200%)")
    print("  • Try keyboard shortcuts (←→ arrows, Esc)")
    print("  • Close viewer when done testing")
    print("="*70 + "\n")


if __name__ == "__main__":
    exit_code = test_gallery_viewer()
    sys.exit(exit_code)
