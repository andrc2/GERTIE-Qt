#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - OPTIMIZED SIMPLE DESIGN
- Shows 8 most recent thumbnails in 2x4 grid
- Scroll to see previous batches (stored as simple data, not widgets)
- Filename below thumbnail
- Maximum performance and responsiveness
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QCursor
from image_viewer import ImageViewer


class ThumbnailWidget(QFrame):
    """Single thumbnail - image above, filename below"""
    
    clicked = Signal(str)  # Emits filepath when clicked
    
    # 25% larger: was ~140x90, now 175x113
    THUMB_WIDTH = 175
    THUMB_HEIGHT = 113
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            ThumbnailWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
            }
            ThumbnailWidget:hover {
                border: 2px solid #4a9eff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMB_WIDTH, self.THUMB_HEIGHT)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1a1a1a;")
        layout.addWidget(self.image_label)
        
        # Filename below (no "Capturing..." status)
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setStyleSheet("color: #aaa; font-size: 9px;")
        self.filename_label.setFixedWidth(self.THUMB_WIDTH)
        layout.addWidget(self.filename_label)
        
        self.setFixedSize(self.THUMB_WIDTH + 10, self.THUMB_HEIGHT + 24)
    
    def set_preview(self, pixmap: QPixmap, camera_id: int):
        """Set preview from video frame - just show camera number"""
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(self.THUMB_WIDTH, self.THUMB_HEIGHT,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.FastTransformation)
            self.image_label.setPixmap(scaled)
        self.filename_label.setText(f"rep{camera_id}")
        self.filepath = None
    
    def set_file(self, filepath: str, pixmap: QPixmap = None):
        """Link to actual hi-res file"""
        self.filepath = filepath
        # Short filename: rep1_20260119_141234.jpg -> rep1_141234
        name = os.path.basename(filepath)
        short = name.replace('.jpg', '').replace('_2026', '_').replace('01', '')
        self.filename_label.setText(short)
        
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(self.THUMB_WIDTH, self.THUMB_HEIGHT,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.FastTransformation)
            self.image_label.setPixmap(scaled)
    
    def mousePressEvent(self, event):
        if self.filepath and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
    
    def clear(self):
        self.image_label.clear()
        self.filename_label.clear()
        self.filepath = None


class GalleryPanel(QWidget):
    """
    Optimized gallery showing 8 thumbnails at a time.
    Stores history as lightweight data, creates widgets only for visible items.
    """
    
    MAX_HISTORY = 200  # Max items to remember
    ITEMS_PER_PAGE = 8  # 2x4 grid
    
    def __init__(self, captures_dir="hires_captures", parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        os.makedirs(self.captures_dir, exist_ok=True)
        
        # Data storage (lightweight - just paths and pixmaps)
        self.items = []  # List of {'camera_id': int, 'pixmap': QPixmap, 'filepath': str or None}
        self.current_page = 0
        
        # Viewer
        self.viewer = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header with count
        header = QHBoxLayout()
        self.title_label = QLabel("📷 Gallery")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #fff;")
        header.addWidget(self.title_label)
        
        self.count_label = QLabel("0 images")
        self.count_label.setStyleSheet("color: #888; font-size: 10px;")
        header.addStretch()
        header.addWidget(self.count_label)
        layout.addLayout(header)
        
        # Navigation (prev/next page)
        nav = QHBoxLayout()
        self.prev_btn = QLabel("◀ Older")
        self.prev_btn.setStyleSheet("color: #666; font-size: 10px;")
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.mousePressEvent = lambda e: self._prev_page()
        nav.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("color: #888; font-size: 10px;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.page_label)
        
        self.next_btn = QLabel("Newer ▶")
        self.next_btn.setStyleSheet("color: #4a9eff; font-size: 10px;")
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.mousePressEvent = lambda e: self._next_page()
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)
        
        # Grid container for 8 thumbnails (2 columns x 4 rows)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create 8 reusable thumbnail widgets
        self.thumb_widgets = []
        for i in range(8):
            thumb = ThumbnailWidget()
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self.thumb_widgets.append(thumb)
            row, col = divmod(i, 2)
            self.grid_layout.addWidget(thumb, row, col)
        
        layout.addWidget(self.grid_widget)
        layout.addStretch()
        
        # Set fixed width for gallery panel
        self.setFixedWidth(ThumbnailWidget.THUMB_WIDTH * 2 + 30)
        self.setStyleSheet("background-color: #1e1e1e;")
    
    def add_preview_thumbnail(self, camera_id: int, preview_pixmap: QPixmap):
        """Add instant preview thumbnail from video frame"""
        # Insert at beginning (newest first)
        item = {
            'camera_id': camera_id,
            'pixmap': preview_pixmap,
            'filepath': None
        }
        self.items.insert(0, item)
        
        # Trim history
        if len(self.items) > self.MAX_HISTORY:
            self.items = self.items[:self.MAX_HISTORY]
        
        # Stay on page 0 (newest) and refresh
        self.current_page = 0
        self._refresh_display()
    
    def link_preview_to_file(self, camera_id: int, filepath: str):
        """Link a preview to its actual hi-res file"""
        # Find most recent unlinked item for this camera
        for item in self.items:
            if item['camera_id'] == camera_id and item['filepath'] is None:
                item['filepath'] = filepath
                break
        self._refresh_display()
    
    def _refresh_display(self):
        """Update the 8 visible thumbnails based on current page"""
        start = self.current_page * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        visible_items = self.items[start:end]
        
        # Update widgets
        for i, thumb in enumerate(self.thumb_widgets):
            if i < len(visible_items):
                item = visible_items[i]
                if item['filepath']:
                    thumb.set_file(item['filepath'], item['pixmap'])
                else:
                    thumb.set_preview(item['pixmap'], item['camera_id'])
                thumb.show()
            else:
                thumb.clear()
                thumb.hide()
        
        # Update labels
        total = len(self.items)
        total_pages = max(1, (total + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self.count_label.setText(f"{total} images")
        self.page_label.setText(f"Page {self.current_page + 1}/{total_pages}")
        
        # Update nav button states
        if self.current_page == 0:
            self.next_btn.setStyleSheet("color: #666; font-size: 10px;")
        else:
            self.next_btn.setStyleSheet("color: #4a9eff; font-size: 10px;")
        
        if self.current_page >= total_pages - 1:
            self.prev_btn.setStyleSheet("color: #666; font-size: 10px;")
        else:
            self.prev_btn.setStyleSheet("color: #4a9eff; font-size: 10px;")
    
    def _prev_page(self):
        """Go to older images"""
        total_pages = max(1, (len(self.items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._refresh_display()
    
    def _next_page(self):
        """Go to newer images"""
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_display()
    
    def _on_thumbnail_clicked(self, filepath: str):
        """Open image viewer"""
        if not filepath or not os.path.exists(filepath):
            return
        
        # Collect all linked filepaths
        all_files = [item['filepath'] for item in self.items if item['filepath']]
        
        if self.viewer is None:
            self.viewer = ImageViewer()
            self.viewer.image_deleted.connect(self._on_image_deleted)
        
        self.viewer.show_image(filepath, all_files)
        self.viewer.show()
        self.viewer.raise_()
    
    def _on_image_deleted(self, filepath: str):
        """Handle image deletion"""
        self.items = [item for item in self.items if item['filepath'] != filepath]
        self._refresh_display()
    
    def cleanup(self):
        """Cleanup on close"""
        pass
    
    def stop_auto_refresh(self):
        """Compatibility alias"""
        self.cleanup()
