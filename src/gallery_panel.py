#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - PySide6 Implementation
Displays thumbnails of captured images

Features:
- Scrollable thumbnail grid
- Auto-updates when new captures are added
- Click to view full size (future)
- Organized by camera
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from PIL import Image
from image_viewer import ImageViewer


class ThumbnailWidget(QFrame):
    """Widget displaying a single thumbnail"""
    
    clicked = Signal(str)  # filepath
    
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self._setup_ui()
        self._load_thumbnail()
        
    def _setup_ui(self):
        """Setup the widget UI"""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            ThumbnailWidget {
                background-color: #222;
                border: 2px solid #444;
                border-radius: 5px;
            }
            ThumbnailWidget:hover {
                border-color: #66f;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        self.setLayout(layout)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet("background-color: #000; border: 1px solid #666;")
        layout.addWidget(self.image_label)
        
        # Filename label
        filename = Path(self.filepath).name
        self.name_label = QLabel(filename)
        self.name_label.setStyleSheet("color: white; font-size: 10px;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def _load_thumbnail(self):
        """Load and display thumbnail"""
        try:
            # Load image and create thumbnail
            img = Image.open(self.filepath)
            img.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            # Convert to QPixmap
            img_path = self.filepath + ".thumb"
            img.save(img_path, "JPEG")
            pixmap = QPixmap(img_path)
            self.image_label.setPixmap(pixmap)
            
            # Clean up temp file
            os.remove(img_path)
            
        except Exception as e:
            self.name_label.setText(f"Error: {e}")
            
    def mousePressEvent(self, event):
        """Handle click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)


class GalleryPanel(QWidget):
    """Panel displaying gallery of captured images"""
    
    def __init__(self, captures_dir: str, parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        self.thumbnails = []
        self._setup_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_gallery)
        self.refresh_timer.start(1000)  # Check every second
        
        # Initial load
        self.refresh_gallery()
        
    def _setup_ui(self):
        """Setup the panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setLayout(layout)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📷 Gallery")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Image count
        self.count_label = QLabel("0 images")
        self.count_label.setStyleSheet("color: #aaa; font-size: 12px;")
        header.addWidget(self.count_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_gallery)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Scroll area for thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
        """)
        
        # Container for thumbnails
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout()
        self.thumbnail_layout.setSpacing(10)
        self.thumbnail_container.setLayout(self.thumbnail_layout)
        
        scroll.setWidget(self.thumbnail_container)
        layout.addWidget(scroll)
        
    def refresh_gallery(self):
        """Refresh gallery with current captures"""
        if not os.path.exists(self.captures_dir):
            return
            
        # Get all jpg files
        image_files = sorted(
            [f for f in Path(self.captures_dir).glob("*.jpg")],
            key=lambda x: x.stat().st_mtime,
            reverse=True  # Newest first
        )
        
        # Check if update needed
        current_files = [str(f) for f in image_files]
        existing_files = [t.filepath for t in self.thumbnails]
        
        if current_files == existing_files:
            return  # No changes
            
        # Clear existing thumbnails
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.thumbnails.clear()
        
        # Add thumbnails (4 per row)
        cols = 4
        for i, filepath in enumerate(image_files):
            row = i // cols
            col = i % cols
            
            thumb = ThumbnailWidget(str(filepath))
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self.thumbnail_layout.addWidget(thumb, row, col)
            self.thumbnails.append(thumb)
        
        # Update count
        self.count_label.setText(f"{len(image_files)} images")
        
    def _on_thumbnail_clicked(self, filepath: str):
        """Handle thumbnail click - open full-size viewer"""
        print(f"📷 Opening viewer: {filepath}")
        
        # Get all image files for navigation
        image_files = sorted(
            [str(f) for f in Path(self.captures_dir).glob("*.jpg")],
            key=lambda x: os.path.getmtime(x),
            reverse=True  # Newest first
        )
        
        # Open viewer
        viewer = ImageViewer(filepath, image_files, self)
        viewer.image_deleted.connect(self._on_image_deleted)
        viewer.exec()
    
    def _on_image_deleted(self, filepath: str):
        """Handle image deletion from viewer"""
        print(f"🗑️ Image deleted, refreshing gallery: {filepath}")
        self.refresh_gallery()
        
    def stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        self.refresh_timer.stop()


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    print("Gallery Panel Test")
    
    app = QApplication(sys.argv)
    
    # Create test captures directory
    test_dir = "test_gallery_images"
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate some test images
    from PIL import Image, ImageDraw
    for i in range(12):
        img = Image.new('RGB', (640, 480), color=(i*20, 100, 200-i*10))
        draw = ImageDraw.Draw(img)
        draw.text((250, 220), f"Test Image {i+1}", fill=(255, 255, 255))
        img.save(f"{test_dir}/test_{i:03d}.jpg")
    
    # Create gallery
    gallery = GalleryPanel(test_dir)
    gallery.setMinimumSize(700, 500)
    gallery.setStyleSheet("background-color: #1a1a1a;")
    gallery.show()
    
    # Auto-close after 5 seconds
    from PySide6.QtCore import QTimer
    QTimer.singleShot(5000, app.quit)
    
    exit_code = app.exec()
    
    # Cleanup
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    print(f"✓ Gallery test complete (exit code: {exit_code})")
    sys.exit(exit_code)
