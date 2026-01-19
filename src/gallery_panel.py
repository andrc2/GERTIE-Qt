#!/usr/bin/env python3
"""
Gallery Panel for GERTIE Qt - OPTIMIZED VERSION
Non-blocking thumbnail generation using background thread

Features:
- Background thread for thumbnail creation (no UI blocking)
- Immediate add for new captures via signal
- Cached thumbnails in memory
- Minimal filesystem polling
"""

import os
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QMutex, QMutexLocker
from PySide6.QtGui import QPixmap
from image_viewer import ImageViewer


class ThumbnailWorker(QThread):
    """Background worker for FAST thumbnail generation"""
    
    thumbnail_ready = Signal(str, QPixmap)  # filepath, pixmap
    
    def __init__(self):
        super().__init__()
        self.priority_queue = []  # NEW captures: (filepath, bytes) - process first!
        self.queue = []  # Existing files: filepath only - process after
        self.mutex = QMutex()
        self.running = True
        self._cache = {}  # filepath -> QPixmap cache
    
    def add_to_queue(self, filepath: str, image_data: bytes = None, priority: bool = True):
        """Add file to thumbnail generation queue
        
        Args:
            filepath: Path to the image file
            image_data: Raw JPEG bytes (if available, avoids disk read!)
            priority: True for new captures, False for existing files
        """
        with QMutexLocker(self.mutex):
            if filepath not in self._cache:
                if priority:
                    # Check not already queued
                    if not any(item[0] == filepath for item in self.priority_queue):
                        self.priority_queue.append((filepath, image_data))
                elif filepath not in self.queue:
                    self.queue.append(filepath)
    
    def get_cached(self, filepath: str):
        """Get cached thumbnail if available"""
        with QMutexLocker(self.mutex):
            return self._cache.get(filepath)
    
    def run(self):
        """Process thumbnail queue in background - PRIORITY QUEUE FIRST"""
        while self.running:
            item = None
            filepath = None
            image_data = None
            
            with QMutexLocker(self.mutex):
                # Priority queue first (new captures with bytes)
                if self.priority_queue:
                    item = self.priority_queue.pop(0)
                    filepath, image_data = item
                elif self.queue:
                    filepath = self.queue.pop(0)
                    image_data = None
            
            if filepath:
                pixmap = self._create_thumbnail_fast(filepath, image_data)
                if pixmap:
                    with QMutexLocker(self.mutex):
                        self._cache[filepath] = pixmap
                    self.thumbnail_ready.emit(filepath, pixmap)
            else:
                self.msleep(20)  # Short sleep when queue empty
    
    def _create_thumbnail_fast(self, filepath: str, image_data: bytes = None) -> QPixmap:
        """Create thumbnail FAST - use provided bytes if available, else read from disk"""
        try:
            # Use provided bytes (FAST!) or read from disk (slower)
            if image_data is None:
                with open(filepath, 'rb') as f:
                    image_data = f.read()
            
            # Qt native JPEG decode + fast scale
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                return pixmap.scaled(150, 150, 
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.FastTransformation)
            return None
            
        except Exception as e:
            print(f"Thumbnail error for {filepath}: {e}")
            return None
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
    
    def trim_cache(self, max_size: int):
        """Trim cache to prevent unbounded memory growth"""
        with QMutexLocker(self.mutex):
            if len(self._cache) > max_size:
                # Remove oldest entries (FIFO approximation)
                keys_to_remove = list(self._cache.keys())[:-max_size]
                for key in keys_to_remove:
                    del self._cache[key]


class ThumbnailWidget(QFrame):
    """Widget displaying a single thumbnail"""
    
    clicked = Signal(str)  # filepath
    
    def __init__(self, filepath: str, pixmap: QPixmap = None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self._setup_ui()
        if pixmap:
            self.set_pixmap(pixmap)
        
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
        self.image_label.setText("Loading...")
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
    
    def set_pixmap(self, pixmap: QPixmap):
        """Set the thumbnail pixmap"""
        self.image_label.setPixmap(pixmap)
        self.image_label.setText("")
        
    def mousePressEvent(self, event):
        """Handle click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)


class GalleryPanel(QWidget):
    """Panel displaying gallery of captured images - OPTIMIZED FOR LONG SESSIONS"""
    
    # Limit displayed thumbnails to prevent slowdown
    MAX_VISIBLE_THUMBNAILS = 100
    
    def __init__(self, captures_dir: str, parent=None):
        super().__init__(parent)
        self.captures_dir = captures_dir
        self.thumbnails = {}  # filepath -> ThumbnailWidget (VISIBLE only)
        self.known_files = set()  # Track known files to detect new ones
        self.mtime_cache = {}  # filepath -> mtime (limited size)
        self._pending_insert = []  # Batch inserts for efficiency
        self._setup_ui()
        
        # Background thumbnail worker
        self.thumb_worker = ThumbnailWorker()
        self.thumb_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumb_worker.start()
        
        # Lightweight polling - just checks for new files, doesn't create thumbnails
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._check_for_new_files)
        self.refresh_timer.start(1000)  # Check every 1000ms
        
        # Initial load
        self._check_for_new_files()
        
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
    
    def _check_for_new_files(self):
        """Lightweight check for new files - doesn't block UI"""
        if not os.path.exists(self.captures_dir):
            return
        
        try:
            # Quick directory listing (no stat calls yet)
            current_files = set(str(f) for f in Path(self.captures_dir).glob("*.jpg"))
            
            # Find new files
            new_files = current_files - self.known_files
            removed_files = self.known_files - current_files
            
            # Handle removed files
            for filepath in removed_files:
                if filepath in self.thumbnails:
                    widget = self.thumbnails.pop(filepath)
                    widget.deleteLater()
                self.mtime_cache.pop(filepath, None)
            
            # Queue new files for thumbnail generation (LOW priority - let new captures go first)
            for filepath in new_files:
                # Cache mtime when first seen (avoid repeated stat calls)
                try:
                    self.mtime_cache[filepath] = os.path.getmtime(filepath)
                except:
                    self.mtime_cache[filepath] = 0
                self._add_placeholder(filepath)
                self.thumb_worker.add_to_queue(filepath, priority=False)  # Low priority
            
            self.known_files = current_files
            
            # Update layout if changes
            if new_files or removed_files:
                self._update_layout()
                
        except Exception as e:
            print(f"Gallery check error: {e}")
    
    def _add_placeholder(self, filepath: str):
        """Add placeholder widget for new file (thumbnail loads in background)"""
        if filepath not in self.thumbnails:
            # Check if we have a cached thumbnail
            cached = self.thumb_worker.get_cached(filepath)
            widget = ThumbnailWidget(filepath, cached)
            widget.clicked.connect(self._on_thumbnail_clicked)
            self.thumbnails[filepath] = widget
    
    def _on_thumbnail_ready(self, filepath: str, pixmap: QPixmap):
        """Called when background worker finishes thumbnail"""
        if filepath in self.thumbnails:
            self.thumbnails[filepath].set_pixmap(pixmap)
    
    def _update_layout(self):
        """Update grid layout with current thumbnails - OPTIMIZED with limit"""
        # Clear layout
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            # Don't delete widgets, just remove from layout
        
        # Sort by cached modification time (newest first)
        sorted_files = sorted(
            self.thumbnails.keys(),
            key=lambda f: self.mtime_cache.get(f, 0),
            reverse=True
        )
        
        # Limit to MAX_VISIBLE_THUMBNAILS
        visible_files = sorted_files[:self.MAX_VISIBLE_THUMBNAILS]
        
        # Remove excess from thumbnails dict
        for filepath in sorted_files[self.MAX_VISIBLE_THUMBNAILS:]:
            widget = self.thumbnails.pop(filepath, None)
            if widget:
                widget.deleteLater()
            self.mtime_cache.pop(filepath, None)
        
        # Add to grid (4 per row)
        cols = 4
        for i, filepath in enumerate(visible_files):
            row = i // cols
            col = i % cols
            self.thumbnail_layout.addWidget(self.thumbnails[filepath], row, col)
        
        # Update count
        self.count_label.setText(f"{len(self.thumbnails)} images")
    
    def add_image_immediately(self, filepath: str, image_data: bytes = None):
        """Add new image INSTANTLY - placeholder appears immediately, thumbnail loads in background"""
        if filepath in self.thumbnails:
            return  # Already have it
        
        # Cache mtime
        self.mtime_cache[filepath] = time.time()
        
        # Create widget with NO pixmap (shows "Loading..." placeholder - INSTANT!)
        widget = ThumbnailWidget(filepath, None)
        widget.clicked.connect(self._on_thumbnail_clicked)
        self.thumbnails[filepath] = widget
        self.known_files.add(filepath)
        
        # Insert at position 0,0 and shift others (FAST: only moves pointers)
        self._insert_at_top_fast(widget)
        
        # Enforce limit - remove oldest if over limit
        self._enforce_thumbnail_limit()
        
        # Update count IMMEDIATELY
        self.count_label.setText(f"{len(self.thumbnails)} images")
        
        # Queue thumbnail generation - pass image_data to avoid disk read!
        self.thumb_worker.add_to_queue(filepath, image_data=image_data, priority=True)
    
    def _insert_at_top_fast(self, new_widget):
        """Insert widget at top - O(1) operation using layout index"""
        # Simply insert at position 0 - Qt handles the rest
        self.thumbnail_layout.addWidget(new_widget, 0, 0)
        
        # Rebuild layout only if we have more than a few items
        # This is still O(n) but we limit n to MAX_VISIBLE_THUMBNAILS
        if self.thumbnail_layout.count() > 4:
            self._rebuild_grid_layout()
    
    def _rebuild_grid_layout(self):
        """Rebuild grid layout efficiently"""
        # Collect widgets in current order (newest first based on mtime)
        widgets = []
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item.widget():
                widgets.append(item.widget())
        
        # Sort by mtime (newest first)
        widgets.sort(key=lambda w: self.mtime_cache.get(w.filepath, 0), reverse=True)
        
        # Re-add to grid (4 columns)
        cols = 4
        for i, w in enumerate(widgets):
            row = i // cols
            col = i % cols
            self.thumbnail_layout.addWidget(w, row, col)
    
    def _enforce_thumbnail_limit(self):
        """Remove oldest thumbnails if over limit - prevents memory growth"""
        if len(self.thumbnails) <= self.MAX_VISIBLE_THUMBNAILS:
            return
        
        # Find oldest thumbnails by mtime
        sorted_paths = sorted(
            self.thumbnails.keys(),
            key=lambda p: self.mtime_cache.get(p, 0)
        )
        
        # Remove oldest until under limit
        while len(self.thumbnails) > self.MAX_VISIBLE_THUMBNAILS:
            oldest = sorted_paths.pop(0)
            widget = self.thumbnails.pop(oldest)
            self.mtime_cache.pop(oldest, None)
            # Remove from layout and delete
            self.thumbnail_layout.removeWidget(widget)
            widget.deleteLater()
        
        # Also trim the worker cache
        self.thumb_worker.trim_cache(self.MAX_VISIBLE_THUMBNAILS)
    
    def refresh_gallery(self):
        """Full refresh - clears and reloads everything"""
        # Clear all
        self.thumbnails.clear()
        self.known_files.clear()
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Reload
        self._check_for_new_files()
        
    def _on_thumbnail_clicked(self, filepath: str):
        """Handle thumbnail click - open full-size viewer"""
        print(f"📷 Opening viewer: {filepath}")
        
        # Get all image files for navigation - use cached mtimes
        image_files = sorted(
            [str(f) for f in Path(self.captures_dir).glob("*.jpg")],
            key=lambda x: self.mtime_cache.get(x, 0),
            reverse=True
        )
        
        # Open viewer
        viewer = ImageViewer(filepath, image_files, self)
        viewer.image_deleted.connect(self._on_image_deleted)
        viewer.exec()
    
    def _on_image_deleted(self, filepath: str):
        """Handle image deletion from viewer"""
        print(f"🗑️ Image deleted, refreshing gallery: {filepath}")
        if filepath in self.thumbnails:
            widget = self.thumbnails.pop(filepath)
            widget.deleteLater()
        self.known_files.discard(filepath)
        self._update_layout()
        
    def stop_auto_refresh(self):
        """Stop auto-refresh timer and worker"""
        self.refresh_timer.stop()
        self.thumb_worker.stop()
        self.thumb_worker.wait()


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    print("Gallery Panel Test - OPTIMIZED VERSION")
    
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
