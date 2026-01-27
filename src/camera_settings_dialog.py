#!/usr/bin/env python3
"""
Camera Settings Dialog for GERTIE Qt - PySide6 Implementation
Part 1: UI Layout Only (no functionality yet)

Compatible with original Tkinter system:
- Same settings structure
- Same value ranges
- Same network commands
- Per-camera settings persistence
"""

import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QCheckBox, QGroupBox,
    QComboBox, QScrollArea, QWidget, QSpinBox
)
from PySide6.QtCore import Qt, Signal


class CameraSettingsDialog(QDialog):
    """Camera settings dialog - matches Tkinter functionality"""
    
    settings_applied = Signal(str, dict)  # ip, settings_dict
    
    def __init__(self, ip: str, camera_name: str, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.camera_name = camera_name
        
        # Load saved settings
        self.settings = self.load_camera_settings()
        
        self._setup_ui()
        self._load_values()
        
    def _setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Camera Settings - {self.camera_name} ({self.ip})")
        self.setMinimumSize(500, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: white;
                border: 2px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        self.setLayout(main_layout)
        
        # Title
        title = QLabel(f"📷 {self.camera_name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(10)
        scroll_content.setLayout(scroll_layout)
        
        # === HARDWARE SETTINGS ===
        hardware_group = QGroupBox("Hardware Settings")
        hardware_layout = QVBoxLayout()
        
        # ISO
        iso_layout = QHBoxLayout()
        iso_layout.addWidget(QLabel("ISO:"))
        self.iso_slider = QSlider(Qt.Orientation.Horizontal)
        self.iso_slider.setMinimum(100)
        self.iso_slider.setMaximum(1600)
        self.iso_slider.setValue(400)
        self.iso_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.iso_slider.setTickInterval(100)
        iso_layout.addWidget(self.iso_slider)
        self.iso_label = QLabel("400")
        self.iso_label.setMinimumWidth(50)
        self.iso_label.setStyleSheet("color: #0f0; font-weight: bold;")
        iso_layout.addWidget(self.iso_label)
        hardware_layout.addLayout(iso_layout)
        
        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(-50)
        self.brightness_slider.setMaximum(50)
        self.brightness_slider.setValue(0)
        self.brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness_slider.setTickInterval(10)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_label = QLabel("0")
        self.brightness_label.setMinimumWidth(50)
        self.brightness_label.setStyleSheet("color: #0f0; font-weight: bold;")
        brightness_layout.addWidget(self.brightness_label)
        hardware_layout.addLayout(brightness_layout)
        
        hardware_group.setLayout(hardware_layout)
        scroll_layout.addWidget(hardware_group)
        
        # === IMAGE ADJUSTMENTS ===
        adjustments_group = QGroupBox("Image Adjustments")
        adjustments_layout = QVBoxLayout()
        
        # Flip Horizontal
        self.flip_h_checkbox = QCheckBox("Flip Horizontal")
        self.flip_h_checkbox.setStyleSheet("color: white;")
        adjustments_layout.addWidget(self.flip_h_checkbox)
        
        # Flip Vertical
        self.flip_v_checkbox = QCheckBox("Flip Vertical")
        self.flip_v_checkbox.setStyleSheet("color: white;")
        adjustments_layout.addWidget(self.flip_v_checkbox)
        
        # Grayscale
        self.grayscale_checkbox = QCheckBox("Grayscale")
        self.grayscale_checkbox.setStyleSheet("color: white;")
        adjustments_layout.addWidget(self.grayscale_checkbox)
        
        # Rotation
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("Rotation:"))
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["0°", "90°", "180°", "270°"])
        self.rotation_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
            }
        """)
        rotation_layout.addWidget(self.rotation_combo)
        rotation_layout.addStretch()
        adjustments_layout.addLayout(rotation_layout)
        
        adjustments_group.setLayout(adjustments_layout)
        scroll_layout.addWidget(adjustments_group)
        
        # === CROP SETTINGS ===
        crop_group = QGroupBox("Crop Settings")
        crop_layout = QVBoxLayout()
        
        # Crop Enabled
        self.crop_enabled_checkbox = QCheckBox("Enable Crop")
        self.crop_enabled_checkbox.setStyleSheet("color: white; font-weight: bold;")
        crop_layout.addWidget(self.crop_enabled_checkbox)
        
        # Crop Coordinates - use 4:3 HQ camera sensor dimensions (4056x3040)
        crop_coords_layout = QHBoxLayout()
        
        crop_coords_layout.addWidget(QLabel("X:"))
        self.crop_x_spin = QSpinBox()
        self.crop_x_spin.setRange(0, 4056)  # 4:3 sensor width
        self.crop_x_spin.setStyleSheet("background-color: #333; color: white;")
        crop_coords_layout.addWidget(self.crop_x_spin)
        
        crop_coords_layout.addWidget(QLabel("Y:"))
        self.crop_y_spin = QSpinBox()
        self.crop_y_spin.setRange(0, 3040)  # 4:3 sensor height
        self.crop_y_spin.setStyleSheet("background-color: #333; color: white;")
        crop_coords_layout.addWidget(self.crop_y_spin)
        
        crop_coords_layout.addWidget(QLabel("W:"))
        self.crop_w_spin = QSpinBox()
        self.crop_w_spin.setRange(1, 4056)  # 4:3 sensor width
        self.crop_w_spin.setValue(100)
        self.crop_w_spin.setStyleSheet("background-color: #333; color: white;")
        crop_coords_layout.addWidget(self.crop_w_spin)
        
        crop_coords_layout.addWidget(QLabel("H:"))
        self.crop_h_spin = QSpinBox()
        self.crop_h_spin.setRange(1, 3040)  # 4:3 sensor height
        self.crop_h_spin.setValue(100)
        self.crop_h_spin.setStyleSheet("background-color: #333; color: white;")
        crop_coords_layout.addWidget(self.crop_h_spin)
        
        crop_layout.addLayout(crop_coords_layout)
        
        crop_group.setLayout(crop_layout)
        scroll_layout.addWidget(crop_group)
        
        # === RAW CAPTURE SETTINGS ===
        # Only show for RAW-capable cameras (rep2, rep8)
        self.raw_group = None
        if self._is_raw_capable():
            raw_group = QGroupBox("RAW Capture (DNG)")
            raw_layout = QVBoxLayout()
            
            # RAW Enabled toggle
            self.raw_enabled_checkbox = QCheckBox("Enable RAW Capture")
            self.raw_enabled_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #f90;
                    font-weight: bold;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            self.raw_enabled_checkbox.setToolTip(
                "When enabled, captures both DNG (RAW) and JPEG files.\n"
                "DNG files are ~23MB and take longer to transfer.\n"
                "JPEG is used for gallery preview."
            )
            raw_layout.addWidget(self.raw_enabled_checkbox)
            
            # Info label
            raw_info = QLabel("📷 Captures JPEG (~2MB) + DNG (~23MB)")
            raw_info.setStyleSheet("color: #888; font-size: 11px; margin-left: 20px;")
            raw_layout.addWidget(raw_info)
            
            raw_group.setLayout(raw_layout)
            scroll_layout.addWidget(raw_group)
            self.raw_group = raw_group
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # === BUTTONS ===
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("✓ Apply Settings")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #3b6; }
            QPushButton:pressed { background-color: #194; }
        """)
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #a44;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #b55; }
            QPushButton:pressed { background-color: #933; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # Connect slider value changes to labels (UI feedback only)
        self.iso_slider.valueChanged.connect(
            lambda v: self.iso_label.setText(str(v))
        )
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_label.setText(str(v))
        )
    
    def _is_raw_capable(self):
        """Check if this camera is RAW-capable (rep2 or rep8)"""
        # rep2 = 192.168.0.202 (dorsal), rep8 = 127.0.0.1 (lateral)
        return self.ip in ("192.168.0.202", "127.0.0.1")
    
    def _load_values(self):
        """Load saved values into UI widgets"""
        self.iso_slider.setValue(self.settings.get("iso", 400))
        self.brightness_slider.setValue(self.settings.get("brightness", 0))
        self.flip_h_checkbox.setChecked(self.settings.get("flip_horizontal", False))
        self.flip_v_checkbox.setChecked(self.settings.get("flip_vertical", False))
        self.grayscale_checkbox.setChecked(self.settings.get("grayscale", False))
        
        rotation = self.settings.get("rotation", 0)
        rotation_index = {0: 0, 90: 1, 180: 2, 270: 3}.get(rotation, 0)
        self.rotation_combo.setCurrentIndex(rotation_index)
        
        self.crop_enabled_checkbox.setChecked(self.settings.get("crop_enabled", False))
        self.crop_x_spin.setValue(self.settings.get("crop_x", 0))
        self.crop_y_spin.setValue(self.settings.get("crop_y", 0))
        self.crop_w_spin.setValue(self.settings.get("crop_width", 100))
        self.crop_h_spin.setValue(self.settings.get("crop_height", 100))
        
        # RAW capture setting (only for capable cameras)
        if self._is_raw_capable() and hasattr(self, 'raw_enabled_checkbox'):
            self.raw_enabled_checkbox.setChecked(self.settings.get("raw_enabled", False))
    
    def get_settings_filename(self):
        """Get settings filename for this camera"""
        safe_ip = self.ip.replace(".", "_").replace(":", "_")
        return f"camera_settings_{safe_ip}.json"
    
    def load_camera_settings(self):
        """Load persisted settings for this camera"""
        settings_file = self.get_settings_filename()
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings for {self.ip}: {e}")
        
        # Return defaults matching original system
        return {
            "iso": 400,
            "brightness": 0,
            "flip_horizontal": False,
            "flip_vertical": False,
            "grayscale": False,
            "rotation": 0,
            "crop_enabled": False,
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 100,
            "crop_height": 100,
        }
    
    def apply_settings(self):
        """Apply settings - save and emit signal"""
        print(f"🔧 Applying settings to {self.camera_name} ({self.ip})...")
        
        # Build settings dict
        rotation_degrees = [0, 90, 180, 270][self.rotation_combo.currentIndex()]
        
        settings_dict = {
            "iso": self.iso_slider.value(),
            "brightness": self.brightness_slider.value(),
            "flip_horizontal": self.flip_h_checkbox.isChecked(),
            "flip_vertical": self.flip_v_checkbox.isChecked(),
            "grayscale": self.grayscale_checkbox.isChecked(),
            "rotation": rotation_degrees,
            "crop_enabled": self.crop_enabled_checkbox.isChecked(),
            "crop_x": self.crop_x_spin.value(),
            "crop_y": self.crop_y_spin.value(),
            "crop_width": self.crop_w_spin.value(),
            "crop_height": self.crop_h_spin.value(),
        }
        
        # Add RAW setting if this camera is RAW-capable
        if self._is_raw_capable() and hasattr(self, 'raw_enabled_checkbox'):
            settings_dict["raw_enabled"] = self.raw_enabled_checkbox.isChecked()
        
        # Save to file
        self.save_camera_settings(settings_dict)
        
        # Emit signal for network transmission
        self.settings_applied.emit(self.ip, settings_dict)
        
        print(f"  ✓ Settings saved and emitted")
        self.accept()
    
    def save_camera_settings(self, settings_dict):
        """Save settings to JSON file"""
        settings_file = self.get_settings_filename()
        try:
            with open(settings_file, "w") as f:
                json.dump(settings_dict, f, indent=2)
            print(f"  💾 Settings saved to {settings_file}")
        except Exception as e:
            print(f"  ✗ Error saving settings: {e}")


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    print("Camera Settings Dialog - UI Test (Part 1)")
    print("="*60)
    
    app = QApplication(sys.argv)
    
    # Create test dialog
    dialog = CameraSettingsDialog("192.168.0.201", "REP1")
    dialog.show()
    
    exit_code = app.exec()
    print(f"\n✓ Dialog test complete (exit code: {exit_code})")
    sys.exit(exit_code)
