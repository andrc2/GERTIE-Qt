#!/usr/bin/env python3
"""
Full-Size Image Viewer for GERTIE Qt
Opens when user clicks gallery thumbnail
Features: Navigation, zoom, delete, open folder
"""

import os
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QKeyEvent


class ImageViewer(QDialog):
    """Full-size image viewer with navigation and controls"""
    
    image_deleted = Signal(str)  # image_path
    
    def __init__(self, image_path: str, all_images: list, parent=None):
        super().__init__(parent)
        self.all_images = all_images
        self.current_index = all_images.index(image_path) if image_path in all_images else 0
        self.zoom_level = "fit"  # "fit", "100%", "200%"
        
        self._setup_ui()
        self._load_image()
        
    def _setup_ui(self):
        """Setup viewer UI"""
        self.setWindowTitle("Image Viewer")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #222;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #555;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # === IMAGE INFO ===
        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-size: 12px; color: #aaa;")
        layout.addWidget(self.info_label)
        
        # === IMAGE DISPLAY (scrollable) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #333; background-color: #0a0a0a; }")
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0a0a0a;")
        
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll, stretch=1)
        
        # === CONTROLS ===
        controls_layout = QHBoxLayout()
        
        # Navigation
        self.prev_btn = QPushButton("◀ Previous (←)")
        self.prev_btn.clicked.connect(self._prev_image)
        controls_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next (→) ▶")
        self.next_btn.clicked.connect(self._next_image)
        controls_layout.addWidget(self.next_btn)
        
        controls_layout.addStretch()
        
        # Zoom
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(lambda: self._set_zoom("fit"))
        controls_layout.addWidget(self.zoom_fit_btn)
        
        self.zoom_100_btn = QPushButton("100%")
        self.zoom_100_btn.clicked.connect(lambda: self._set_zoom("100%"))
        controls_layout.addWidget(self.zoom_100_btn)
        
        self.zoom_200_btn = QPushButton("200%")
        self.zoom_200_btn.clicked.connect(lambda: self._set_zoom("200%"))
        controls_layout.addWidget(self.zoom_200_btn)
        
        controls_layout.addStretch()
        
        # Delete
        self.delete_btn = QPushButton("🗑️ Delete (Del)")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #a44;
            }
            QPushButton:hover {
                background-color: #b55;
            }
            QPushButton:pressed {
                background-color: #933;
            }
        """)
        self.delete_btn.clicked.connect(self._delete_image)
        controls_layout.addWidget(self.delete_btn)
        
        # Open Folder button - opens hires_captures in file manager
        open_folder_btn = QPushButton("📁 Open Folder")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #458;
            }
            QPushButton:hover {
                background-color: #569;
            }
        """)
        open_folder_btn.clicked.connect(self._open_folder)
        controls_layout.addWidget(open_folder_btn)
        
        # Close
        close_btn = QPushButton("Close (Esc)")
        close_btn.clicked.connect(self.accept)
        controls_layout.addWidget(close_btn)
        
        layout.addLayout(controls_layout)
        
    def _load_image(self):
        """Load and display current image"""
        if not self.all_images or self.current_index >= len(self.all_images):
            self.info_label.setText("No image to display")
            return
        
        image_path = self.all_images[self.current_index]
        
        if not os.path.exists(image_path):
            self.info_label.setText(f"Image not found: {image_path}")
            return
        
        # Load pixmap
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.info_label.setText(f"Failed to load: {image_path}")
            return
        
        # Apply zoom
        if self.zoom_level == "fit":
            # Fit to window (maintain aspect ratio)
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        elif self.zoom_level == "100%":
            self.image_label.setPixmap(pixmap)
        elif self.zoom_level == "200%":
            scaled = pixmap.scaled(
                pixmap.width() * 2,
                pixmap.height() * 2,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        
        # Update info
        filename = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        file_size_kb = file_size / 1024
        mod_time = datetime.fromtimestamp(os.path.getmtime(image_path))
        
        info = (f"Image {self.current_index + 1}/{len(self.all_images)} | "
                f"{filename} | "
                f"{pixmap.width()}x{pixmap.height()} | "
                f"{file_size_kb:.1f} KB | "
                f"{mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.info_label.setText(info)
        
        # Update button states
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.all_images) - 1)
        
        # Update zoom button highlighting
        for btn in [self.zoom_fit_btn, self.zoom_100_btn, self.zoom_200_btn]:
            btn.setStyleSheet(btn.styleSheet().replace("background-color: #555;", ""))
        
        if self.zoom_level == "fit":
            self.zoom_fit_btn.setStyleSheet("background-color: #555;")
        elif self.zoom_level == "100%":
            self.zoom_100_btn.setStyleSheet("background-color: #555;")
        elif self.zoom_level == "200%":
            self.zoom_200_btn.setStyleSheet("background-color: #555;")
        
    def _prev_image(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self._load_image()
    
    def _next_image(self):
        """Go to next image"""
        if self.current_index < len(self.all_images) - 1:
            self.current_index += 1
            self._load_image()
    
    def _set_zoom(self, level: str):
        """Set zoom level"""
        self.zoom_level = level
        self._load_image()
    
    def _delete_image(self):
        """Delete current image"""
        if not self.all_images or self.current_index >= len(self.all_images):
            return
        
        image_path = self.all_images[self.current_index]
        filename = os.path.basename(image_path)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Image",
            f"Are you sure you want to delete {filename}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(image_path)
                print(f"🗑️ Deleted: {image_path}")
                
                # Emit signal
                self.image_deleted.emit(image_path)
                
                # Remove from list
                self.all_images.pop(self.current_index)
                
                # Load next image or close if no more images
                if not self.all_images:
                    QMessageBox.information(self, "No Images", "No more images to display")
                    self.accept()
                else:
                    # Stay at same index (shows next image) or go back if at end
                    if self.current_index >= len(self.all_images):
                        self.current_index = len(self.all_images) - 1
                    self._load_image()
                    
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Failed to delete image: {e}")
    
    def _open_folder(self):
        """Open the folder containing hi-res images in the system file manager"""
        if not self.all_images:
            return
        
        # Get the folder path from current image
        image_path = self.all_images[self.current_index]
        folder_path = os.path.dirname(os.path.abspath(image_path))
        
        try:
            system = platform.system()
            if system == "Linux":
                # Try multiple file managers (Raspberry Pi uses PCManFM by default)
                file_managers = [
                    ["pcmanfm", folder_path],           # Raspberry Pi default
                    ["nautilus", folder_path],          # GNOME
                    ["thunar", folder_path],            # XFCE
                    ["dolphin", folder_path],           # KDE
                    ["xdg-open", folder_path],          # Generic Linux
                ]
                
                opened = False
                for fm_cmd in file_managers:
                    try:
                        subprocess.Popen(fm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        opened = True
                        print(f"📁 Opened folder: {folder_path}")
                        break
                    except FileNotFoundError:
                        continue
                
                if not opened:
                    QMessageBox.warning(self, "Open Folder", 
                                       f"Could not find file manager.\nFolder path:\n{folder_path}")
            
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", folder_path])
                print(f"📁 Opened folder: {folder_path}")
            
            elif system == "Windows":
                subprocess.Popen(["explorer", folder_path])
                print(f"📁 Opened folder: {folder_path}")
            
            else:
                QMessageBox.information(self, "Folder Path", 
                                       f"Hi-res images folder:\n{folder_path}")
                
        except Exception as e:
            QMessageBox.warning(self, "Open Folder Error", 
                               f"Could not open folder:\n{e}\n\nPath: {folder_path}")
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Left:
            self._prev_image()
        elif event.key() == Qt.Key_Right:
            self._next_image()
        elif event.key() == Qt.Key_Delete:
            self._delete_image()
        elif event.key() == Qt.Key_Escape:
            self.accept()
        elif event.key() == Qt.Key_F:
            self._set_zoom("fit")
        elif event.key() == Qt.Key_1:
            self._set_zoom("100%")
        elif event.key() == Qt.Key_2:
            self._set_zoom("200%")
        else:
            super().keyPressEvent(event)


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    import glob
    
    print("Image Viewer - Test")
    print("="*60)
    
    app = QApplication(sys.argv)
    
    # Find test images
    images = sorted(glob.glob("captures/*.jpg"))
    
    if not images:
        print("✗ No test images found in captures/")
        sys.exit(1)
    
    print(f"Found {len(images)} images")
    
    # Open viewer with first image
    viewer = ImageViewer(images[0], images)
    viewer.image_deleted.connect(lambda path: print(f"  Deleted: {path}"))
    viewer.show()
    
    exit_code = app.exec()
    print(f"\n✓ Viewer test complete (exit code: {exit_code})")
    sys.exit(exit_code)
