#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - SCROLLABLE with RESIZABLE THUMBNAILS
- Scroll bar navigation (shows 8 at a time)
- Thumbnails scale proportionally when gallery resizes
- Click to open ImageViewer
- Maximum performance
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor
from image_viewer import ImageViewer


class ThumbnailWidget(QFrame):
    """Scalable thumbnail - image above, filename below"""
    
    clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.original_pixmap = None
        self.camera_id = 0
        
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
        layout.setContentsMargins(3, 3, 3, 2)
        layout.setSpacing(2)
        
        # Thumbnail image - scales with widget
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1a1a1a; border-radius: 2px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.image_label, 1)
        
        # Filename below
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setStyleSheet("color: #aaa; font-size: 9px;")
        self.filename_label.setFixedHeight(14)
        layout.addWidget(self.filename_label)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def set_preview(self, pixmap: QPixmap, camera_id: int):
        """Set preview from video frame"""
        self.original_pixmap = pixmap
        self.camera_id = camera_id
        self.filepath = None
        self.filename_label.setText(f"rep{camera_id}")
        self._update_scaled_pixmap()
    
    def set_file(self, filepath: str, pixmap: QPixmap = None):
        """Link to actual hi-res file"""
        self.filepath = filepath
        if pixmap:
            self.original_pixmap = pixmap
        name = os.path.basename(filepath)
        short = name.replace('.jpg', '').replace('_2026', '_').replace('01', '')
        self.filename_label.setText(short)
        self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        """Scale pixmap to fit current widget size"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            w = self.image_label.width() - 4
            h = self.image_label.height() - 4
            if w > 20 and h > 20:
                scaled = self.original_pixmap.scaled(
                    w, h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                self.image_label.setPixmap(scaled)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()
    
    def mousePressEvent(self, event):
        if self.filepath and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
    
    def clear(self):
        self.image_label.clear()
        self.filename_label.clear()
        self.filepath = None
        self.original_pixmap = None


class GalleryPanel(QWidget):
    """
    Scrollable 1x8 gallery with resizable thumbnails.
    Scroll bar for navigation, thumbnails scale with panel size.
    """
    
    MAX_HISTORY = 200
    VISIBLE_COUNT = 8
    
    def __init__(self, captures_dir="hires_captures", parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        os.makedirs(self.captures_dir, exist_ok=True)
        
        self.items = []
        self.scroll_position = 0
        self.viewer = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)
        
        # Thumbnails container
        thumb_container = QWidget()
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setSpacing(2)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("📷 Gallery")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #fff;")
        header.addWidget(self.title_label)
        header.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #888; font-size: 10px;")
        header.addWidget(self.count_label)
        thumb_layout.addLayout(header)
        
        # 8 thumbnail widgets
        self.thumb_widgets = []
        for i in range(self.VISIBLE_COUNT):
            thumb = ThumbnailWidget()
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self.thumb_widgets.append(thumb)
            thumb_layout.addWidget(thumb, 1)
        
        main_layout.addWidget(thumb_container, 1)
        
        # Scroll bar
        self.scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.scrollbar.setStyleSheet("""
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a9eff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.scrollbar.valueChanged.connect(self._on_scroll)
        main_layout.addWidget(self.scrollbar)
        
        self.setStyleSheet("background-color: #1e1e1e;")
        self.setMinimumWidth(120)
    
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
        
        self.scroll_position = 0
        self._update_scrollbar()
        self._refresh_display()
    
    def link_preview_to_file(self, camera_id: int, filepath: str):
        """Link preview to hi-res file"""
        for item in self.items:
            if item['camera_id'] == camera_id and item['filepath'] is None:
                item['filepath'] = filepath
                break
        self._refresh_display()
    
    def _update_scrollbar(self):
        max_scroll = max(0, len(self.items) - self.VISIBLE_COUNT)
        self.scrollbar.setRange(0, max_scroll)
        self.scrollbar.setValue(self.scroll_position)
        self.scrollbar.setVisible(max_scroll > 0)
    
    def _on_scroll(self, value):
        self.scroll_position = value
        self._refresh_display()
    
    def _refresh_display(self):
        visible = self.items[self.scroll_position:self.scroll_position + self.VISIBLE_COUNT]
        
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
        
        self.count_label.setText(str(len(self.items)))
    
    def _on_thumbnail_clicked(self, filepath: str):
        """Open image viewer - FIXED: pass required arguments"""
        if not filepath or not os.path.exists(filepath):
            return
        
        all_files = [item['filepath'] for item in self.items if item['filepath']]
        if not all_files:
            return
        
        # Create viewer with REQUIRED arguments
        self.viewer = ImageViewer(filepath, all_files, self)
        self.viewer.image_deleted.connect(self._on_image_deleted)
        self.viewer.show()
    
    def _on_image_deleted(self, filepath: str):
        self.items = [item for item in self.items if item['filepath'] != filepath]
        self._update_scrollbar()
        self._refresh_display()
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        max_scroll = max(0, len(self.items) - self.VISIBLE_COUNT)
        if delta > 0:
            self.scrollbar.setValue(max(0, self.scroll_position - 1))
        else:
            self.scrollbar.setValue(min(max_scroll, self.scroll_position + 1))
    
    def cleanup(self):
        pass
    
    def stop_auto_refresh(self):
        self.cleanup()
