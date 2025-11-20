#!/usr/bin/env python3
"""
Camera Settings Dialog for GERTIE Qt - PySide6 Implementation
Per-camera control settings

Features:
- ISO control (100-1600)
- Brightness (-50 to +50)
- Contrast (0-100)
- Saturation (0-100)
- Flip horizontal/vertical
- Grayscale mode
- Rotation (0, 90, 180, 270)
- Settings persistence (JSON)
- Apply to camera via NetworkManager
"""

import os
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QSlider, QCheckBox, QComboBox, QPushButton,
    QGroupBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal


class CameraSettingsDialog(QDialog):
    """Dialog for per-camera settings"""
    
    settings_changed = Signal(str, dict)  # ip, settings
    
    def __init__(self, camera_id: int, ip: str, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.ip = ip
        self.settings_file = f"camera_settings_{ip.replace('.', '_')}.json"
        
        self.setWindowTitle(f"Camera Settings - REP{camera_id} ({ip})")
        self.setModal(True)
        self.setMinimumSize(500, 600)
        
        # Load settings
        self.settings = self._load_settings()
        
        # Setup UI
        self._setup_ui()
        
    def _load_settings(self) -> dict:
        """Load settings from file or use defaults"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Default settings
        return {
            'iso': 400,
            'brightness': 0,
            'contrast': 50,
            'saturation': 50,
            'flip_horizontal': False,
            'flip_vertical': False,
            'grayscale': False,
            'rotation': 0
        }
    
    def _save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"✓ Settings saved for {self.ip}")
        except Exception as e:
            print(f"✗ Error saving settings: {e}")
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Header
        header = QLabel(f"REP{self.camera_id} Camera Settings")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: white;
                padding: 10px;
                background-color: #2a5;
                border-radius: 5px;
            }
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_widget.setLayout(content_layout)
        
        # Exposure Controls
        exposure_group = self._create_exposure_controls()
        content_layout.addWidget(exposure_group)
        
        # Image Adjustments
        image_group = self._create_image_adjustments()
        content_layout.addWidget(image_group)
        
        # Transform Controls
        transform_group = self._create_transform_controls()
        content_layout.addWidget(transform_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Bottom buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: white;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #444;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2a5;
                border: 1px solid #5a5;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #3b6;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #444;
                border-radius: 3px;
                background: #222;
            }
            QCheckBox::indicator:checked {
                background: #2a5;
                border-color: #5a5;
            }
            QComboBox {
                background: #333;
                color: white;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #333;
                color: white;
                selection-background-color: #2a5;
            }
        """)
    
    def _create_exposure_controls(self) -> QGroupBox:
        """Create exposure control group"""
        group = QGroupBox("Exposure Controls")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # ISO
        iso_layout = QHBoxLayout()
        iso_label = QLabel("ISO:")
        iso_label.setMinimumWidth(100)
        self.iso_slider = QSlider(Qt.Orientation.Horizontal)
        self.iso_slider.setMinimum(100)
        self.iso_slider.setMaximum(1600)
        self.iso_slider.setValue(self.settings['iso'])
        self.iso_value_label = QLabel(str(self.settings['iso']))
        self.iso_value_label.setMinimumWidth(50)
        self.iso_slider.valueChanged.connect(
            lambda v: self.iso_value_label.setText(str(v))
        )
        iso_layout.addWidget(iso_label)
        iso_layout.addWidget(self.iso_slider)
        iso_layout.addWidget(self.iso_value_label)
        layout.addLayout(iso_layout)
        
        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_label = QLabel("Brightness:")
        brightness_label.setMinimumWidth(100)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(-50)
        self.brightness_slider.setMaximum(50)
        self.brightness_slider.setValue(self.settings['brightness'])
        self.brightness_value_label = QLabel(str(self.settings['brightness']))
        self.brightness_value_label.setMinimumWidth(50)
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_value_label.setText(str(v))
        )
        brightness_layout.addWidget(brightness_label)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_value_label)
        layout.addLayout(brightness_layout)
        
        return group
    
    def _create_image_adjustments(self) -> QGroupBox:
        """Create image adjustment group"""
        group = QGroupBox("Image Adjustments")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # Contrast
        contrast_layout = QHBoxLayout()
        contrast_label = QLabel("Contrast:")
        contrast_label.setMinimumWidth(100)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.setValue(self.settings['contrast'])
        self.contrast_value_label = QLabel(str(self.settings['contrast']))
        self.contrast_value_label.setMinimumWidth(50)
        self.contrast_slider.valueChanged.connect(
            lambda v: self.contrast_value_label.setText(str(v))
        )
        contrast_layout.addWidget(contrast_label)
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_value_label)
        layout.addLayout(contrast_layout)
        
        # Saturation
        saturation_layout = QHBoxLayout()
        saturation_label = QLabel("Saturation:")
        saturation_label.setMinimumWidth(100)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(100)
        self.saturation_slider.setValue(self.settings['saturation'])
        self.saturation_value_label = QLabel(str(self.settings['saturation']))
        self.saturation_value_label.setMinimumWidth(50)
        self.saturation_slider.valueChanged.connect(
            lambda v: self.saturation_value_label.setText(str(v))
        )
        saturation_layout.addWidget(saturation_label)
        saturation_layout.addWidget(self.saturation_slider)
        saturation_layout.addWidget(self.saturation_value_label)
        layout.addLayout(saturation_layout)
        
        return group
    
    def _create_transform_controls(self) -> QGroupBox:
        """Create transform control group"""
        group = QGroupBox("Transform Controls")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # Flip controls
        flip_layout = QHBoxLayout()
        self.flip_h_checkbox = QCheckBox("Flip Horizontal")
        self.flip_h_checkbox.setChecked(self.settings['flip_horizontal'])
        self.flip_v_checkbox = QCheckBox("Flip Vertical")
        self.flip_v_checkbox.setChecked(self.settings['flip_vertical'])
        flip_layout.addWidget(self.flip_h_checkbox)
        flip_layout.addWidget(self.flip_v_checkbox)
        flip_layout.addStretch()
        layout.addLayout(flip_layout)
        
        # Grayscale
        self.grayscale_checkbox = QCheckBox("Grayscale Mode")
        self.grayscale_checkbox.setChecked(self.settings['grayscale'])
        layout.addWidget(self.grayscale_checkbox)
        
        # Rotation
        rotation_layout = QHBoxLayout()
        rotation_label = QLabel("Rotation:")
        rotation_label.setMinimumWidth(100)
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["0°", "90°", "180°", "270°"])
        rotation_index = [0, 90, 180, 270].index(self.settings['rotation'])
        self.rotation_combo.setCurrentIndex(rotation_index)
        rotation_layout.addWidget(rotation_label)
        rotation_layout.addWidget(self.rotation_combo)
        rotation_layout.addStretch()
        layout.addLayout(rotation_layout)
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """Create bottom button layout"""
        layout = QHBoxLayout()
        
        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #c44;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d55; }
            QPushButton:pressed { background-color: #a33; }
        """)
        reset_btn.clicked.connect(self._reset_defaults)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # Apply button
        apply_btn = QPushButton("Apply Settings")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3b6; }
            QPushButton:pressed { background-color: #194; }
        """)
        apply_btn.clicked.connect(self._apply_settings)
        layout.addWidget(apply_btn)
        
        return layout
    
    def _reset_defaults(self):
        """Reset all settings to defaults"""
        self.iso_slider.setValue(400)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(50)
        self.saturation_slider.setValue(50)
        self.flip_h_checkbox.setChecked(False)
        self.flip_v_checkbox.setChecked(False)
        self.grayscale_checkbox.setChecked(False)
        self.rotation_combo.setCurrentIndex(0)
        print(f"Reset settings for {self.ip} to defaults")
    
    def _apply_settings(self):
        """Apply and save settings"""
        # Update settings dict
        self.settings = {
            'iso': self.iso_slider.value(),
            'brightness': self.brightness_slider.value(),
            'contrast': self.contrast_slider.value(),
            'saturation': self.saturation_slider.value(),
            'flip_horizontal': self.flip_h_checkbox.isChecked(),
            'flip_vertical': self.flip_v_checkbox.isChecked(),
            'grayscale': self.grayscale_checkbox.isChecked(),
            'rotation': [0, 90, 180, 270][self.rotation_combo.currentIndex()]
        }
        
        # Save to file
        self._save_settings()
        
        # Emit signal
        self.settings_changed.emit(self.ip, self.settings)
        
        print(f"\n📸 Applied settings for REP{self.camera_id}:")
        for key, value in self.settings.items():
            print(f"  {key}: {value}")
        
        # Close dialog
        self.accept()


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    print("Camera Settings Dialog Test")
    
    app = QApplication(sys.argv)
    
    # Create dialog
    dialog = CameraSettingsDialog(1, "192.168.0.201")
    
    # Connect signal
    def on_settings_changed(ip, settings):
        print(f"\n✓ Settings applied for {ip}:")
        print(f"  Settings: {settings}")
    
    dialog.settings_changed.connect(on_settings_changed)
    
    # Show
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        print("\n✓ Dialog accepted")
    else:
        print("\n✗ Dialog cancelled")
    
    sys.exit(0)
