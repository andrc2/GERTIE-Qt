#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - VERTICAL 1x8 LAYOUT
- Single column, 8 thumbnails visible
- Pagination for older batches (no scroll lag)
- Maximum performance and responsiveness
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor
from image_viewer import ImageViewer


class ThumbnailWidget(QFrame):
    """Compact horizontal thumbnail - image left, filename right"""
    
    clicked = Signal(str)
    
    # 25% larger than original
    THUMB_WIDTH = 175
    THUMB_HEIGHT = 113
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            ThumbnailWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 3px;
            }
            ThumbnailWidget:hover {
                border: 1px solid #4a9eff;
                background-color: #333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 2)
        layout.setSpacing(2)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMB_WIDTH, self.THUMB_HEIGHT)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1a1a1a; border-radius: 2px;")
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Filename below
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setStyleSheet("color: #aaa; font-size: 9px;")
        layout.addWidget(self.filename_label)
        
        self.setFixedHeight(self.THUMB_HEIGHT + 22)
    
    def set_preview(self, pixmap: QPixmap, camera_id: int):
        """Set preview from video frame"""
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
        name = os.path.basename(filepath)
        # Short: rep1_20260119_151234.jpg -> rep1_151234
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
    Vertical 1x8 gallery with pagination.
    Fixed 8 widgets, data stored separately for performance.
    """
    
    MAX_HISTORY = 200
    ITEMS_PER_PAGE = 8
    
    def __init__(self, captures_dir="hires_captures", parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        os.makedirs(self.captures_dir, exist_ok=True)
        
        self.items = []  # Lightweight data storage
        self.current_page = 0
        self.viewer = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("📷 Gallery")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #fff;")
        header.addWidget(self.title_label)
        header.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #888; font-size: 10px;")
        header.addWidget(self.count_label)
        layout.addLayout(header)
        
        # Navigation
        nav = QHBoxLayout()
        self.prev_btn = QLabel("◀")
        self.prev_btn.setStyleSheet("color: #666; font-size: 12px;")
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.mousePressEvent = lambda e: self._prev_page()
        nav.addWidget(self.prev_btn)
        
        self.page_label = QLabel("1/1")
        self.page_label.setStyleSheet("color: #888; font-size: 9px;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.page_label, 1)
        
        self.next_btn = QLabel("▶")
        self.next_btn.setStyleSheet("color: #666; font-size: 12px;")
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.mousePressEvent = lambda e: self._next_page()
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)
        
        # 8 thumbnail widgets in vertical stack
        self.thumb_widgets = []
        for i in range(8):
            thumb = ThumbnailWidget()
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self.thumb_widgets.append(thumb)
            layout.addWidget(thumb)
        
        layout.addStretch()
        
        # Fixed width for single column
        self.setFixedWidth(ThumbnailWidget.THUMB_WIDTH + 16)
        self.setStyleSheet("background-color: #1e1e1e;")
    
    def add_preview_thumbnail(self, camera_id: int, preview_pixmap: QPixmap):
        """Add instant preview thumbnail"""
        item = {
            'camera_id': camera_id,
            'pixmap': preview_pixmap,
            'filepath': None
        }
        self.items.insert(0, item)
        
        if len(self.items) > self.MAX_HISTORY:
            self.items = self.items[:self.MAX_HISTORY]
        
        self.current_page = 0
        self._refresh_display()
    
    def link_preview_to_file(self, camera_id: int, filepath: str):
        """Link preview to hi-res file"""
        for item in self.items:
            if item['camera_id'] == camera_id and item['filepath'] is None:
                item['filepath'] = filepath
                break
        self._refresh_display()
    
    def _refresh_display(self):
        """Update visible thumbnails"""
        start = self.current_page * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        visible = self.items[start:end]
        
        for i, thumb in enumerate(self.thumb_widgets):
            if i < len(visible):
                item = visible[i]
                if item['filepath']:
                    thumb.set_file(item['filepath'], item['pixmap'])
                else:
                    thumb.set_preview(item['pixmap'], item['camera_id'])
                thumb.show()
            else:
                thumb.clear()
                thumb.hide()
        
        total = len(self.items)
        pages = max(1, (total + 7) // 8)
        self.count_label.setText(str(total))
        self.page_label.setText(f"{self.current_page + 1}/{pages}")
        
        # Nav colors
        self.next_btn.setStyleSheet(f"color: {'#666' if self.current_page == 0 else '#4a9eff'}; font-size: 12px;")
        self.prev_btn.setStyleSheet(f"color: {'#666' if self.current_page >= pages - 1 else '#4a9eff'}; font-size: 12px;")
    
    def _prev_page(self):
        """Older images"""
        pages = max(1, (len(self.items) + 7) // 8)
        if self.current_page < pages - 1:
            self.current_page += 1
            self._refresh_display()
    
    def _next_page(self):
        """Newer images"""
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_display()
    
    def _on_thumbnail_clicked(self, filepath: str):
        """Open viewer"""
        if not filepath or not os.path.exists(filepath):
            return
        
        all_files = [item['filepath'] for item in self.items if item['filepath']]
        
        if self.viewer is None:
            self.viewer = ImageViewer()
            self.viewer.image_deleted.connect(self._on_image_deleted)
        
        self.viewer.show_image(filepath, all_files)
        self.viewer.show()
        self.viewer.raise_()
    
    def _on_image_deleted(self, filepath: str):
        """Handle deletion"""
        self.items = [item for item in self.items if item['filepath'] != filepath]
        self._refresh_display()
    
    def cleanup(self):
        pass
    
    def stop_auto_refresh(self):
        self.cleanup()
