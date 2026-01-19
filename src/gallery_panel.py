#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - TRUE VIRTUAL SCROLLING
Only visible thumbnails exist as widgets - massive performance gain

Architecture:
- DATA: List of all image paths (can be 1000s)
- WIDGETS: Only ~10 recycled widgets for visible area
- On scroll: Update widget contents, don't create/destroy
"""

import os
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSizePolicy, QScrollBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QMutex, QMutexLocker, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from image_viewer import ImageViewer


# =============================================================================
# THUMBNAIL CACHE (Shared cache for pixmaps)
# =============================================================================

class ThumbnailCache:
    """Thread-safe cache for thumbnail pixmaps"""
    
    def __init__(self, max_size=100):
        self.cache = {}  # filepath -> QPixmap
        self.max_size = max_size
        self.access_order = []  # LRU tracking
        self.mutex = QMutex()
    
    def get(self, filepath):
        with QMutexLocker(self.mutex):
            if filepath in self.cache:
                # Move to end (most recently used)
                if filepath in self.access_order:
                    self.access_order.remove(filepath)
                self.access_order.append(filepath)
                return self.cache[filepath]
        return None
    
    def put(self, filepath, pixmap):
        with QMutexLocker(self.mutex):
            if filepath not in self.cache:
                # Evict oldest if at capacity
                while len(self.cache) >= self.max_size and self.access_order:
                    oldest = self.access_order.pop(0)
                    self.cache.pop(oldest, None)
            
            self.cache[filepath] = pixmap
            if filepath in self.access_order:
                self.access_order.remove(filepath)
            self.access_order.append(filepath)
    
    def has(self, filepath):
        with QMutexLocker(self.mutex):
            return filepath in self.cache


# =============================================================================
# THUMBNAIL LOADER (Background thread)
# =============================================================================

class ThumbnailLoader(QThread):
    """Background loader for thumbnails"""
    
    loaded = Signal(str, QPixmap)  # filepath, pixmap
    
    THUMB_WIDTH = 140
    THUMB_HEIGHT = 90
    
    def __init__(self, cache: ThumbnailCache):
        super().__init__()
        self.cache = cache
        self.queue = []
        self.mutex = QMutex()
        self.running = True
    
    def request(self, filepath: str, priority: bool = False):
        """Request thumbnail load"""
        if self.cache.has(filepath):
            return  # Already cached
        
        with QMutexLocker(self.mutex):
            if filepath not in self.queue:
                if priority:
                    self.queue.insert(0, filepath)
                else:
                    self.queue.append(filepath)
    
    def run(self):
        while self.running:
            filepath = None
            with QMutexLocker(self.mutex):
                if self.queue:
                    filepath = self.queue.pop(0)
            
            if filepath and not self.cache.has(filepath):
                pixmap = self._load(filepath)
                if pixmap:
                    self.cache.put(filepath, pixmap)
                    self.loaded.emit(filepath, pixmap)
            else:
                self.msleep(30)
    
    def _load(self, filepath: str) -> QPixmap:
        try:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                return pixmap.scaled(self.THUMB_WIDTH, self.THUMB_HEIGHT,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.FastTransformation)
        except Exception as e:
            pass
        return None
    
    def stop(self):
        self.running = False


# =============================================================================
# VIRTUAL LIST WIDGET (The magic - only renders visible items)
# =============================================================================

class VirtualThumbnailList(QWidget):
    """Virtual scrolling list - only visible thumbnails consume resources"""
    
    item_clicked = Signal(str)  # filepath
    
    ITEM_HEIGHT = 75  # Height of each row
    VISIBLE_BUFFER = 2  # Extra items above/below visible area
    
    def __init__(self, cache: ThumbnailCache, parent=None):
        super().__init__(parent)
        self.cache = cache
        
        # DATA: All items (filepath, preview_pixmap or None)
        self.items = []  # [(filepath, preview_pixmap), ...]
        
        # Scroll state
        self.scroll_offset = 0
        self.visible_height = 600
        
        # Preview pixmaps for pending items
        self.preview_pixmaps = {}  # camera_id -> pixmap
        
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def set_scroll(self, offset: int, visible_height: int):
        """Update scroll position"""
        self.scroll_offset = offset
        self.visible_height = visible_height
        self.update()  # Trigger repaint
    
    def add_item(self, filepath: str, preview_pixmap: QPixmap = None):
        """Add item at top of list"""
        # Remove if exists
        self.items = [(fp, px) for fp, px in self.items if fp != filepath]
        # Insert at top
        self.items.insert(0, (filepath, preview_pixmap))
        self._update_size()
        self.update()
    
    def update_item(self, old_filepath: str, new_filepath: str):
        """Update item filepath (when hi-res arrives)"""
        for i, (fp, px) in enumerate(self.items):
            if fp == old_filepath:
                self.items[i] = (new_filepath, px)
                break
        self.update()
    
    def remove_item(self, filepath: str):
        """Remove item"""
        self.items = [(fp, px) for fp, px in self.items if fp != filepath]
        self._update_size()
        self.update()
    
    def _update_size(self):
        """Update widget size based on item count"""
        total_height = len(self.items) * self.ITEM_HEIGHT
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)
    
    def get_visible_range(self):
        """Get indices of visible items"""
        first = max(0, self.scroll_offset // self.ITEM_HEIGHT - self.VISIBLE_BUFFER)
        last = min(len(self.items), 
                   (self.scroll_offset + self.visible_height) // self.ITEM_HEIGHT + self.VISIBLE_BUFFER + 1)
        return first, last
    
    def paintEvent(self, event):
        """Paint only visible items - THE PERFORMANCE SECRET"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        first, last = self.get_visible_range()
        
        for i in range(first, last):
            if i >= len(self.items):
                break
            
            filepath, preview_pixmap = self.items[i]
            y = i * self.ITEM_HEIGHT
            
            self._paint_item(painter, 0, y, self.width(), self.ITEM_HEIGHT, 
                           filepath, preview_pixmap, i)
        
        painter.end()
    
    def _paint_item(self, painter, x, y, w, h, filepath, preview_pixmap, index):
        """Paint a single item"""
        # Background
        bg_color = QColor("#2a2a2a") if index % 2 == 0 else QColor("#252525")
        painter.fillRect(x, y, w, h, bg_color)
        
        # Border
        painter.setPen(QColor("#444"))
        painter.drawRect(x + 2, y + 2, w - 4, h - 4)
        
        # Thumbnail area
        thumb_x = x + 5
        thumb_y = y + 5
        thumb_w = 100
        thumb_h = h - 10
        
        # Get pixmap (prefer cache, then preview, then placeholder)
        pixmap = self.cache.get(filepath)
        if pixmap is None and preview_pixmap:
            pixmap = preview_pixmap
        
        if pixmap and not pixmap.isNull():
            # Scale to fit
            scaled = pixmap.scaled(thumb_w, thumb_h,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.FastTransformation)
            # Center in thumbnail area
            px = thumb_x + (thumb_w - scaled.width()) // 2
            py = thumb_y + (thumb_h - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)
        else:
            # Placeholder
            painter.fillRect(thumb_x, thumb_y, thumb_w, thumb_h, QColor("#1a1a1a"))
            painter.setPen(QColor("#666"))
            painter.drawText(thumb_x, thumb_y, thumb_w, thumb_h,
                           Qt.AlignmentFlag.AlignCenter, "⏳")
        
        # Text info
        text_x = thumb_x + thumb_w + 10
        text_y = y + 5
        text_w = w - text_x - 5
        
        painter.setPen(QColor("#ddd"))
        painter.setFont(QFont("", 10, QFont.Weight.Bold))
        
        # Filename
        if filepath.startswith("__pending"):
            name = "📷 Capturing..."
            camera = self._extract_camera(filepath)
        else:
            name = Path(filepath).name
            camera = self._extract_camera(filepath)
        
        # Truncate long names
        if len(name) > 25:
            name = name[:22] + "..."
        
        painter.drawText(text_x, text_y + 15, name)
        
        painter.setPen(QColor("#888"))
        painter.setFont(QFont("", 9))
        painter.drawText(text_x, text_y + 35, camera)
    
    def _extract_camera(self, filepath):
        """Extract camera info from filepath"""
        name = Path(filepath).name
        if "__pending_camera_" in filepath:
            try:
                cam = filepath.split("__pending_camera_")[1].replace("__", "")
                return f"Camera {cam} (preview)"
            except:
                pass
        if name.startswith("rep") and "_" in name:
            try:
                cam = name.split("_")[0].replace("rep", "")
                return f"Camera {cam}"
            except:
                pass
        return ""
    
    def mousePressEvent(self, event):
        """Handle click - determine which item was clicked"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Map click to item index
            click_y = event.pos().y()
            index = click_y // self.ITEM_HEIGHT
            
            if 0 <= index < len(self.items):
                filepath, _ = self.items[index]
                self.item_clicked.emit(filepath)
    
    def item_count(self):
        return len(self.items)
    
    def get_all_filepaths(self):
        """Get list of all filepaths (for viewer navigation)"""
        return [fp for fp, _ in self.items if not fp.startswith("__pending")]


# =============================================================================
# GALLERY PANEL (Main widget)
# =============================================================================

class GalleryPanel(QWidget):
    """Gallery panel with virtual scrolling - only visible items use resources"""
    
    MAX_ITEMS = 500  # Maximum items to track
    
    def __init__(self, captures_dir: str, parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        self.known_files = set()
        self.pending_previews = {}  # camera_id -> temp_filepath
        
        # Shared cache and loader
        self.cache = ThumbnailCache(max_size=100)
        self.loader = ThumbnailLoader(self.cache)
        self.loader.loaded.connect(self._on_thumbnail_loaded)
        self.loader.start()
        
        self._setup_ui()
        
        # Periodic check for new files
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._check_for_new_files)
        self.refresh_timer.start(2000)
        
        # Initial load
        QTimer.singleShot(100, self._check_for_new_files)
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setLayout(layout)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("📷 Gallery")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.count_label = QLabel("0 images")
        self.count_label.setStyleSheet("color: #aaa; font-size: 11px;")
        header.addWidget(self.count_label)
        
        layout.addLayout(header)
        
        # Scroll area with virtual list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: #1a1a1a; }
            QScrollBar:vertical { width: 10px; background: #2a2a2a; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #777; }
        """)
        
        # Virtual list
        self.virtual_list = VirtualThumbnailList(self.cache)
        self.virtual_list.item_clicked.connect(self._on_item_clicked)
        
        self.scroll_area.setWidget(self.virtual_list)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        layout.addWidget(self.scroll_area)
    
    def _on_scroll(self, value):
        """Update virtual list with scroll position"""
        visible_height = self.scroll_area.viewport().height()
        self.virtual_list.set_scroll(value, visible_height)
        
        # Request thumbnails for visible items
        first, last = self.virtual_list.get_visible_range()
        for i in range(first, min(last, len(self.virtual_list.items))):
            filepath, _ = self.virtual_list.items[i]
            if not filepath.startswith("__pending"):
                self.loader.request(filepath)
    
    def _check_for_new_files(self):
        """Check for new files on disk"""
        if not os.path.exists(self.captures_dir):
            return
        
        try:
            current_files = set(str(f) for f in Path(self.captures_dir).glob("*.jpg"))
            new_files = current_files - self.known_files
            
            # Sort by mtime (newest first) and add
            for filepath in sorted(new_files, key=lambda f: os.path.getmtime(f), reverse=True):
                self.virtual_list.add_item(filepath)
                self.loader.request(filepath, priority=False)
            
            self.known_files = current_files
            self._update_count()
            
            # Enforce limit
            while self.virtual_list.item_count() > self.MAX_ITEMS:
                if self.virtual_list.items:
                    old_fp, _ = self.virtual_list.items[-1]
                    self.virtual_list.remove_item(old_fp)
                    self.known_files.discard(old_fp)
            
        except Exception as e:
            print(f"Gallery scan error: {e}")
    
    def _on_thumbnail_loaded(self, filepath: str, pixmap: QPixmap):
        """Thumbnail loaded from disk - trigger repaint"""
        self.virtual_list.update()
    
    def _on_item_clicked(self, filepath: str):
        """Handle item click"""
        if filepath.startswith("__pending"):
            print(f"📷 Preview clicked - hi-res still loading...")
            return
        
        print(f"📷 Opening viewer: {filepath}")
        all_files = self.virtual_list.get_all_filepaths()
        if filepath in all_files:
            viewer = ImageViewer(filepath, all_files, self)
            viewer.image_deleted.connect(self._on_image_deleted)
            viewer.exec()
    
    def _on_image_deleted(self, filepath: str):
        """Handle image deletion"""
        self.virtual_list.remove_item(filepath)
        self.known_files.discard(filepath)
        self._update_count()
    
    def _update_count(self):
        total = self.virtual_list.item_count()
        self.count_label.setText(f"{total} images")
    
    # =========================================================================
    # PUBLIC API - Instant preview thumbnails
    # =========================================================================
    
    def add_preview_thumbnail(self, camera_id: int, preview_pixmap):
        """Add INSTANT preview thumbnail from video frame"""
        print(f"    🖼️ add_preview_thumbnail called for camera {camera_id}")
        
        # Remove existing preview for this camera
        if camera_id in self.pending_previews:
            old_fp = self.pending_previews.pop(camera_id)
            self.virtual_list.remove_item(old_fp)
        
        # Add new preview
        temp_filepath = f"__pending_camera_{camera_id}__"
        
        # Scale preview to thumbnail size
        thumb = preview_pixmap.scaled(140, 90,
                                      Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.FastTransformation)
        
        self.virtual_list.add_item(temp_filepath, thumb)
        self.pending_previews[camera_id] = temp_filepath
        
        self._update_count()
        print(f"    ✅ Preview thumbnail added for camera {camera_id} - total now: {self.virtual_list.item_count()}")
    
    def link_preview_to_file(self, camera_id: int, filepath: str):
        """Link pending preview to actual hi-res file"""
        if camera_id in self.pending_previews:
            old_fp = self.pending_previews.pop(camera_id)
            self.virtual_list.update_item(old_fp, filepath)
            self.known_files.add(filepath)
        else:
            # No pending preview - add directly
            self.virtual_list.add_item(filepath)
            self.known_files.add(filepath)
            self.loader.request(filepath, priority=True)
        
        self._update_count()
    
    def refresh_gallery(self):
        """Manual refresh"""
        self._check_for_new_files()
    
    def cleanup(self):
        """Cleanup on close"""
        self.refresh_timer.stop()
        self.loader.stop()
        self.loader.wait()
