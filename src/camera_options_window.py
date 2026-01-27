#!/usr/bin/env python3
"""
Camera Options Window for GERTIE Qt
Comprehensive camera settings with live preview and WYSIWYG capture

Features:
- Tabbed interface: Exposure, Color, Processing, Focus, Capture, Advanced
- Real-time preview updates via Picamera2 controls
- High-res capture via libcamera-still with matching settings
- Per-camera settings persistence
"""

import json
import os
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QGroupBox, QComboBox, QSpinBox,
    QTabWidget, QWidget, QScrollArea, QDoubleSpinBox,
    QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class CameraOptionsWindow(QDialog):
    """
    Comprehensive Camera Options Window
    Unifies all camera adjustments with live preview and WYSIWYG capture
    """
    
    # Signal emitted when settings are applied
    settings_changed = Signal(str, dict)  # ip, settings_dict
    
    # Picamera2 control ranges (from libcamera documentation)
    CONTROL_RANGES = {
        'brightness': {'min': -1.0, 'max': 1.0, 'default': 0.0, 'gui_min': -100, 'gui_max': 100},
        'contrast': {'min': 0.0, 'max': 2.0, 'default': 1.0, 'gui_min': 0, 'gui_max': 100},
        'saturation': {'min': 0.0, 'max': 2.0, 'default': 1.0, 'gui_min': 0, 'gui_max': 100},
        'sharpness': {'min': 0.0, 'max': 16.0, 'default': 1.0, 'gui_min': 0, 'gui_max': 100},
        'exposure_compensation': {'min': -8.0, 'max': 8.0, 'default': 0.0},
        'analogue_gain': {'min': 1.0, 'max': 16.0, 'default': 1.0},  # ISO equivalent
    }
    
    # White balance presets (ColourGains for Picamera2)
    WB_PRESETS = {
        'Auto': None,
        'Daylight': (1.5, 1.2),
        'Cloudy': (1.6, 1.2),
        'Tungsten': (1.0, 1.8),
        'Fluorescent': (1.3, 1.5),
        'Indoor': (1.2, 1.6),
        'Flash': (1.5, 1.2),
    }
    
    # Exposure modes
    EXPOSURE_MODES = ['Auto', 'Manual', 'Short', 'Long']
    
    # AWB modes available in libcamera
    AWB_MODES = ['Auto', 'Incandescent', 'Tungsten', 'Fluorescent', 
                 'Indoor', 'Daylight', 'Cloudy']
    
    def __init__(self, ip: str, camera_name: str, network_manager=None, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.camera_name = camera_name
        self.network_manager = network_manager
        
        # Settings storage
        self.settings = self._load_settings()
        self._pending_changes = {}  # Track changes before apply
        
        self._setup_ui()
        self._load_values_to_ui()
        self._connect_signals()
        
        logger.info(f"[OPTIONS] Camera options opened for {camera_name} ({ip})")
    
    def _setup_ui(self):
        """Setup the tabbed UI"""
        self.setWindowTitle(f"Camera Options - {self.camera_name}")
        self.setMinimumSize(600, 700)
        self.setStyleSheet(self._get_stylesheet())
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # Header
        header = QLabel(f"📷 {self.camera_name} ({self.ip})")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; color: #4af;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; background: #1a1a1a; }
            QTabBar::tab { 
                background: #333; color: #aaa; padding: 8px 16px; 
                border: 1px solid #444; border-bottom: none;
            }
            QTabBar::tab:selected { background: #1a1a1a; color: white; }
            QTabBar::tab:hover { background: #444; }
        """)
        
        # Create tabs
        self._create_exposure_tab()
        self._create_color_tab()
        self._create_processing_tab()
        self._create_focus_tab()
        self._create_capture_tab()
        self._create_advanced_tab()
        
        main_layout.addWidget(self.tabs, 1)
        
        # Button bar
        self._create_button_bar(main_layout)
    
    def _create_exposure_tab(self):
        """Exposure & Light settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Brightness
        self.brightness_slider, self.brightness_label = self._create_slider_control(
            layout, "Brightness", -100, 100, 0, 
            "Adjusts overall image brightness (-100 to +100)"
        )
        
        # Contrast
        self.contrast_slider, self.contrast_label = self._create_slider_control(
            layout, "Contrast", 0, 100, 50,
            "Adjusts image contrast (0=flat, 50=normal, 100=high)"
        )
        
        # Exposure Compensation
        self.exp_comp_slider, self.exp_comp_label = self._create_slider_control(
            layout, "Exposure Compensation (EV)", -30, 30, 0,
            "Exposure compensation in 1/10 EV steps (-3 to +3 EV)"
        )
        
        # ISO / Analogue Gain
        iso_group = QGroupBox("ISO / Sensitivity")
        iso_layout = QVBoxLayout()
        
        self.iso_auto_checkbox = QCheckBox("Auto ISO")
        self.iso_auto_checkbox.setChecked(True)
        iso_layout.addWidget(self.iso_auto_checkbox)
        
        self.iso_slider, self.iso_label = self._create_slider_control(
            iso_layout, "ISO", 100, 3200, 400,
            "Manual ISO setting (100-3200)"
        )
        
        iso_group.setLayout(iso_layout)
        layout.addWidget(iso_group)
        
        # Shutter Speed
        shutter_group = QGroupBox("Shutter Speed")
        shutter_layout = QVBoxLayout()
        
        self.shutter_auto_checkbox = QCheckBox("Auto Shutter")
        self.shutter_auto_checkbox.setChecked(True)
        shutter_layout.addWidget(self.shutter_auto_checkbox)
        
        shutter_row = QHBoxLayout()
        shutter_row.addWidget(QLabel("Shutter (µs):"))
        self.shutter_spin = QSpinBox()
        self.shutter_spin.setRange(100, 1000000)  # 100µs to 1s
        self.shutter_spin.setValue(10000)  # 10ms default
        self.shutter_spin.setSingleStep(1000)
        self.shutter_spin.setStyleSheet("background: #333; color: white; padding: 5px;")
        shutter_row.addWidget(self.shutter_spin)
        shutter_row.addWidget(QLabel("(1/100s = 10000µs)"))
        shutter_row.addStretch()
        shutter_layout.addLayout(shutter_row)
        
        shutter_group.setLayout(shutter_layout)
        layout.addWidget(shutter_group)
        
        # AGC (Automatic Gain Control)
        self.agc_checkbox = QCheckBox("Automatic Gain Control (AGC)")
        self.agc_checkbox.setChecked(True)
        self.agc_checkbox.setToolTip("Enable automatic gain adjustment")
        layout.addWidget(self.agc_checkbox)
        
        layout.addStretch()
        self.tabs.addTab(tab, "📊 Exposure")
    
    def _create_color_tab(self):
        """Color & White Balance settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Saturation
        self.saturation_slider, self.saturation_label = self._create_slider_control(
            layout, "Saturation", 0, 100, 50,
            "Color saturation (0=grayscale, 50=normal, 100=vivid)"
        )
        
        # White Balance Mode
        wb_group = QGroupBox("White Balance")
        wb_layout = QVBoxLayout()
        
        wb_mode_row = QHBoxLayout()
        wb_mode_row.addWidget(QLabel("Mode:"))
        self.wb_combo = QComboBox()
        self.wb_combo.addItems(self.AWB_MODES)
        self.wb_combo.setStyleSheet("background: #333; color: white; padding: 5px;")
        wb_mode_row.addWidget(self.wb_combo)
        wb_mode_row.addStretch()
        wb_layout.addLayout(wb_mode_row)
        
        # Manual Color Temperature (when not Auto)
        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Color Temp (K):"))
        self.color_temp_spin = QSpinBox()
        self.color_temp_spin.setRange(2500, 10000)
        self.color_temp_spin.setValue(5500)
        self.color_temp_spin.setSingleStep(100)
        self.color_temp_spin.setStyleSheet("background: #333; color: white; padding: 5px;")
        temp_row.addWidget(self.color_temp_spin)
        temp_row.addWidget(QLabel("(2500=warm, 5500=daylight, 10000=cool)"))
        temp_row.addStretch()
        wb_layout.addLayout(temp_row)
        
        wb_group.setLayout(wb_layout)
        layout.addWidget(wb_group)
        
        # Manual Color Gains
        gains_group = QGroupBox("Manual Color Gains (Advanced)")
        gains_layout = QGridLayout()
        
        self.manual_gains_checkbox = QCheckBox("Enable Manual Gains")
        gains_layout.addWidget(self.manual_gains_checkbox, 0, 0, 1, 4)
        
        gains_layout.addWidget(QLabel("Red:"), 1, 0)
        self.red_gain_spin = QDoubleSpinBox()
        self.red_gain_spin.setRange(0.5, 3.0)
        self.red_gain_spin.setValue(1.5)
        self.red_gain_spin.setSingleStep(0.1)
        self.red_gain_spin.setStyleSheet("background: #333; color: #f88; padding: 5px;")
        gains_layout.addWidget(self.red_gain_spin, 1, 1)
        
        gains_layout.addWidget(QLabel("Blue:"), 1, 2)
        self.blue_gain_spin = QDoubleSpinBox()
        self.blue_gain_spin.setRange(0.5, 3.0)
        self.blue_gain_spin.setValue(1.2)
        self.blue_gain_spin.setSingleStep(0.1)
        self.blue_gain_spin.setStyleSheet("background: #333; color: #88f; padding: 5px;")
        gains_layout.addWidget(self.blue_gain_spin, 1, 3)
        
        gains_group.setLayout(gains_layout)
        layout.addWidget(gains_group)
        
        # Grayscale option
        self.grayscale_checkbox = QCheckBox("Grayscale / Monochrome")
        self.grayscale_checkbox.setToolTip("Convert output to grayscale")
        layout.addWidget(self.grayscale_checkbox)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🎨 Color")
    
    def _create_processing_tab(self):
        """Image Processing settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Sharpness
        self.sharpness_slider, self.sharpness_label = self._create_slider_control(
            layout, "Sharpness", 0, 100, 50,
            "Edge sharpening (0=soft, 50=normal, 100=very sharp)"
        )
        
        # Noise Reduction
        denoise_group = QGroupBox("Noise Reduction")
        denoise_layout = QVBoxLayout()
        
        denoise_row = QHBoxLayout()
        denoise_row.addWidget(QLabel("Mode:"))
        self.denoise_combo = QComboBox()
        self.denoise_combo.addItems(['Off', 'Fast', 'High Quality'])
        self.denoise_combo.setCurrentIndex(1)  # Fast default
        self.denoise_combo.setStyleSheet("background: #333; color: white; padding: 5px;")
        denoise_row.addWidget(self.denoise_combo)
        denoise_row.addStretch()
        denoise_layout.addLayout(denoise_row)
        
        denoise_group.setLayout(denoise_layout)
        layout.addWidget(denoise_group)
        
        # Lens Shading Correction
        self.lens_shading_checkbox = QCheckBox("Lens Shading Correction")
        self.lens_shading_checkbox.setChecked(True)
        self.lens_shading_checkbox.setToolTip("Correct for lens vignetting")
        layout.addWidget(self.lens_shading_checkbox)
        
        # HDR (if supported)
        hdr_group = QGroupBox("Dynamic Range")
        hdr_layout = QVBoxLayout()
        
        self.hdr_checkbox = QCheckBox("Enable HDR Mode")
        self.hdr_checkbox.setToolTip("High Dynamic Range (requires sensor support)")
        hdr_layout.addWidget(self.hdr_checkbox)
        
        hdr_group.setLayout(hdr_layout)
        layout.addWidget(hdr_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "⚙️ Processing")
    
    def _create_focus_tab(self):
        """Focus & Lens settings (limited for fixed-focus HQ camera)"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Note about HQ Camera
        note = QLabel(
            "ℹ️ The Raspberry Pi HQ Camera has a manual focus lens.\n"
            "Adjust focus physically using the lens focus ring."
        )
        note.setStyleSheet("color: #888; padding: 10px; background: #252525; border-radius: 5px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Digital Zoom / Crop
        zoom_group = QGroupBox("Digital Zoom / Crop")
        zoom_layout = QVBoxLayout()
        
        self.zoom_enabled_checkbox = QCheckBox("Enable Digital Zoom")
        zoom_layout.addWidget(self.zoom_enabled_checkbox)
        
        self.zoom_slider, self.zoom_label = self._create_slider_control(
            zoom_layout, "Zoom Level", 100, 400, 100,
            "Digital zoom (100%=no zoom, 400%=4x zoom)"
        )
        
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)
        
        # Crop ROI
        crop_group = QGroupBox("Crop Region (ROI)")
        crop_layout = QVBoxLayout()
        
        self.crop_enabled_checkbox = QCheckBox("Enable Custom Crop")
        crop_layout.addWidget(self.crop_enabled_checkbox)
        
        # Crop coordinates (4056x3040 sensor)
        coords_layout = QGridLayout()
        coords_layout.addWidget(QLabel("X:"), 0, 0)
        self.crop_x_spin = QSpinBox()
        self.crop_x_spin.setRange(0, 4056)
        self.crop_x_spin.setStyleSheet("background: #333; color: white;")
        coords_layout.addWidget(self.crop_x_spin, 0, 1)
        
        coords_layout.addWidget(QLabel("Y:"), 0, 2)
        self.crop_y_spin = QSpinBox()
        self.crop_y_spin.setRange(0, 3040)
        self.crop_y_spin.setStyleSheet("background: #333; color: white;")
        coords_layout.addWidget(self.crop_y_spin, 0, 3)
        
        coords_layout.addWidget(QLabel("Width:"), 1, 0)
        self.crop_w_spin = QSpinBox()
        self.crop_w_spin.setRange(64, 4056)
        self.crop_w_spin.setValue(4056)
        self.crop_w_spin.setStyleSheet("background: #333; color: white;")
        coords_layout.addWidget(self.crop_w_spin, 1, 1)
        
        coords_layout.addWidget(QLabel("Height:"), 1, 2)
        self.crop_h_spin = QSpinBox()
        self.crop_h_spin.setRange(64, 3040)
        self.crop_h_spin.setValue(3040)
        self.crop_h_spin.setStyleSheet("background: #333; color: white;")
        coords_layout.addWidget(self.crop_h_spin, 1, 3)
        
        crop_layout.addLayout(coords_layout)
        
        # Sensor info
        sensor_info = QLabel("Sensor: 4056 × 3040 (4:3)")
        sensor_info.setStyleSheet("color: #666; font-size: 11px;")
        crop_layout.addWidget(sensor_info)
        
        crop_group.setLayout(crop_layout)
        layout.addWidget(crop_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🔍 Focus")
    
    def _create_capture_tab(self):
        """Capture settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # JPEG Quality
        quality_group = QGroupBox("JPEG Quality")
        quality_layout = QVBoxLayout()
        
        self.quality_slider, self.quality_label = self._create_slider_control(
            quality_layout, "Quality", 50, 100, 95,
            "JPEG compression quality (50=small file, 100=best quality)"
        )
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # RAW Capture (only for capable cameras)
        if self._is_raw_capable():
            raw_group = QGroupBox("RAW Capture (DNG)")
            raw_group.setStyleSheet("""
                QGroupBox { 
                    border: 2px solid #f90; 
                    color: #f90;
                }
            """)
            raw_layout = QVBoxLayout()
            
            self.raw_enabled_checkbox = QCheckBox("Enable RAW Capture")
            self.raw_enabled_checkbox.setStyleSheet("color: #f90; font-weight: bold; font-size: 13px;")
            self.raw_enabled_checkbox.setToolTip(
                "Capture DNG (RAW) files alongside JPEG.\n"
                "DNG files are ~23MB and contain unprocessed sensor data."
            )
            raw_layout.addWidget(self.raw_enabled_checkbox)
            
            raw_info = QLabel(
                "📷 RAW captures both:\n"
                "  • JPEG (~2MB) - For preview and quick use\n"
                "  • DNG (~23MB) - Unprocessed sensor data for post-processing"
            )
            raw_info.setStyleSheet("color: #888; font-size: 11px; padding-left: 20px;")
            raw_layout.addWidget(raw_info)
            
            raw_group.setLayout(raw_layout)
            layout.addWidget(raw_group)
        else:
            no_raw_label = QLabel("ℹ️ RAW capture not available for this camera")
            no_raw_label.setStyleSheet("color: #666; padding: 10px;")
            layout.addWidget(no_raw_label)
        
        # Metadata options
        meta_group = QGroupBox("Metadata / EXIF")
        meta_layout = QVBoxLayout()
        
        self.exif_checkbox = QCheckBox("Include EXIF Metadata")
        self.exif_checkbox.setChecked(True)
        meta_layout.addWidget(self.exif_checkbox)
        
        self.timestamp_checkbox = QCheckBox("Add Timestamp to Filename")
        self.timestamp_checkbox.setChecked(True)
        meta_layout.addWidget(self.timestamp_checkbox)
        
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "📸 Capture")
    
    def _create_advanced_tab(self):
        """Advanced / Experimental settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Warning
        warning = QLabel("⚠️ Advanced settings - modify with caution")
        warning.setStyleSheet("color: #fa0; padding: 10px; background: #332200; border-radius: 5px;")
        layout.addWidget(warning)
        
        # Frame Rate
        fps_group = QGroupBox("Frame Rate")
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Preview FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(5, 60)
        self.fps_spin.setValue(30)
        self.fps_spin.setStyleSheet("background: #333; color: white; padding: 5px;")
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        fps_group.setLayout(fps_layout)
        layout.addWidget(fps_group)
        
        # Flip / Mirror
        flip_group = QGroupBox("Orientation")
        flip_layout = QVBoxLayout()
        
        self.flip_h_checkbox = QCheckBox("Flip Horizontal (Mirror)")
        flip_layout.addWidget(self.flip_h_checkbox)
        
        self.flip_v_checkbox = QCheckBox("Flip Vertical")
        flip_layout.addWidget(self.flip_v_checkbox)
        
        rot_row = QHBoxLayout()
        rot_row.addWidget(QLabel("Rotation:"))
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(['0°', '90°', '180°', '270°'])
        self.rotation_combo.setStyleSheet("background: #333; color: white; padding: 5px;")
        rot_row.addWidget(self.rotation_combo)
        rot_row.addStretch()
        flip_layout.addLayout(rot_row)
        
        flip_group.setLayout(flip_layout)
        layout.addWidget(flip_group)
        
        # Test Pattern
        test_group = QGroupBox("Test Patterns")
        test_layout = QVBoxLayout()
        
        self.test_pattern_checkbox = QCheckBox("Enable Test Pattern")
        self.test_pattern_checkbox.setToolTip("Display sensor test pattern instead of live image")
        test_layout.addWidget(self.test_pattern_checkbox)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Sensor Mode
        sensor_group = QGroupBox("Sensor Mode")
        sensor_layout = QVBoxLayout()
        
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.sensor_mode_combo = QComboBox()
        self.sensor_mode_combo.addItems([
            'Auto',
            'Mode 0: 4056x3040 (Full)',
            'Mode 1: 2028x1520 (2x2 binned)',
            'Mode 2: 1332x990 (Cropped)'
        ])
        self.sensor_mode_combo.setStyleSheet("background: #333; color: white; padding: 5px;")
        mode_row.addWidget(self.sensor_mode_combo)
        sensor_layout.addLayout(mode_row)
        
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🔧 Advanced")
    
    def _create_button_bar(self, parent_layout):
        """Create the bottom button bar"""
        button_layout = QHBoxLayout()
        
        # Reset to Defaults
        reset_btn = QPushButton("↺ Reset Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # Apply
        apply_btn = QPushButton("✓ Apply")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #3b6; }
        """)
        apply_btn.clicked.connect(self._apply_settings)
        button_layout.addWidget(apply_btn)
        
        # Cancel
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #a44;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #b55; }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        parent_layout.addLayout(button_layout)
    
    def _create_slider_control(self, parent_layout, label: str, min_val: int, max_val: int, 
                                default: int, tooltip: str = "") -> tuple:
        """Helper to create a labeled slider with value display"""
        row = QHBoxLayout()
        
        lbl = QLabel(f"{label}:")
        lbl.setMinimumWidth(120)
        row.addWidget(lbl)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval((max_val - min_val) // 10)
        if tooltip:
            slider.setToolTip(tooltip)
        row.addWidget(slider, 1)
        
        value_label = QLabel(str(default))
        value_label.setMinimumWidth(50)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("color: #0f0; font-weight: bold; background: #222; padding: 3px; border-radius: 3px;")
        row.addWidget(value_label)
        
        # Connect slider to label
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        
        if isinstance(parent_layout, QVBoxLayout):
            parent_layout.addLayout(row)
        elif isinstance(parent_layout, QGroupBox):
            parent_layout.layout().addLayout(row)
        
        return slider, value_label
    
    def _is_raw_capable(self) -> bool:
        """Check if camera supports RAW capture (rep2, rep8)"""
        return self.ip in ("192.168.0.202", "127.0.0.1")
    
    def _get_stylesheet(self) -> str:
        """Return the dialog stylesheet"""
        return """
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; }
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
            QCheckBox { color: white; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4af;
                border: 1px solid #4af;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover { background: #5bf; }
        """
    
    def _connect_signals(self):
        """Connect UI signals for live preview updates"""
        # These would send immediate updates to preview
        # For now, changes are batched and applied on "Apply" click
        pass
    
    def _load_settings(self) -> dict:
        """Load persisted settings for this camera"""
        filename = self._get_settings_filename()
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[OPTIONS] Failed to load settings: {e}")
        
        return self._get_default_settings()
    
    def _save_settings(self, settings: dict):
        """Save settings to file"""
        filename = self._get_settings_filename()
        try:
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info(f"[OPTIONS] Settings saved to {filename}")
        except Exception as e:
            logger.error(f"[OPTIONS] Failed to save settings: {e}")
    
    def _get_settings_filename(self) -> str:
        """Get settings filename for this camera"""
        safe_ip = self.ip.replace(".", "_").replace(":", "_")
        return f"camera_options_{safe_ip}.json"
    
    def _get_default_settings(self) -> dict:
        """Return default settings"""
        return {
            # Exposure
            'brightness': 0,
            'contrast': 50,
            'exp_compensation': 0,
            'iso_auto': True,
            'iso': 400,
            'shutter_auto': True,
            'shutter_us': 10000,
            'agc_enabled': True,
            
            # Color
            'saturation': 50,
            'wb_mode': 'Auto',
            'color_temp': 5500,
            'manual_gains': False,
            'red_gain': 1.5,
            'blue_gain': 1.2,
            'grayscale': False,
            
            # Processing
            'sharpness': 50,
            'denoise_mode': 'Fast',
            'lens_shading': True,
            'hdr_enabled': False,
            
            # Focus/Crop
            'zoom_enabled': False,
            'zoom_level': 100,
            'crop_enabled': False,
            'crop_x': 0,
            'crop_y': 0,
            'crop_width': 4056,
            'crop_height': 3040,
            
            # Capture
            'jpeg_quality': 95,
            'raw_enabled': False,
            'exif_enabled': True,
            'timestamp_filename': True,
            
            # Advanced
            'fps': 30,
            'flip_horizontal': False,
            'flip_vertical': False,
            'rotation': 0,
            'test_pattern': False,
            'sensor_mode': 'Auto',
        }
    
    def _load_values_to_ui(self):
        """Load settings values into UI widgets"""
        s = self.settings
        
        # Exposure
        self.brightness_slider.setValue(s.get('brightness', 0))
        self.contrast_slider.setValue(s.get('contrast', 50))
        self.exp_comp_slider.setValue(s.get('exp_compensation', 0))
        self.iso_auto_checkbox.setChecked(s.get('iso_auto', True))
        self.iso_slider.setValue(s.get('iso', 400))
        self.shutter_auto_checkbox.setChecked(s.get('shutter_auto', True))
        self.shutter_spin.setValue(s.get('shutter_us', 10000))
        self.agc_checkbox.setChecked(s.get('agc_enabled', True))
        
        # Color
        self.saturation_slider.setValue(s.get('saturation', 50))
        wb_idx = self.wb_combo.findText(s.get('wb_mode', 'Auto'))
        if wb_idx >= 0:
            self.wb_combo.setCurrentIndex(wb_idx)
        self.color_temp_spin.setValue(s.get('color_temp', 5500))
        self.manual_gains_checkbox.setChecked(s.get('manual_gains', False))
        self.red_gain_spin.setValue(s.get('red_gain', 1.5))
        self.blue_gain_spin.setValue(s.get('blue_gain', 1.2))
        self.grayscale_checkbox.setChecked(s.get('grayscale', False))
        
        # Processing
        self.sharpness_slider.setValue(s.get('sharpness', 50))
        denoise_idx = self.denoise_combo.findText(s.get('denoise_mode', 'Fast'))
        if denoise_idx >= 0:
            self.denoise_combo.setCurrentIndex(denoise_idx)
        self.lens_shading_checkbox.setChecked(s.get('lens_shading', True))
        self.hdr_checkbox.setChecked(s.get('hdr_enabled', False))
        
        # Focus/Crop
        self.zoom_enabled_checkbox.setChecked(s.get('zoom_enabled', False))
        self.zoom_slider.setValue(s.get('zoom_level', 100))
        self.crop_enabled_checkbox.setChecked(s.get('crop_enabled', False))
        self.crop_x_spin.setValue(s.get('crop_x', 0))
        self.crop_y_spin.setValue(s.get('crop_y', 0))
        self.crop_w_spin.setValue(s.get('crop_width', 4056))
        self.crop_h_spin.setValue(s.get('crop_height', 3040))
        
        # Capture
        self.quality_slider.setValue(s.get('jpeg_quality', 95))
        if self._is_raw_capable() and hasattr(self, 'raw_enabled_checkbox'):
            self.raw_enabled_checkbox.setChecked(s.get('raw_enabled', False))
        self.exif_checkbox.setChecked(s.get('exif_enabled', True))
        self.timestamp_checkbox.setChecked(s.get('timestamp_filename', True))
        
        # Advanced
        self.fps_spin.setValue(s.get('fps', 30))
        self.flip_h_checkbox.setChecked(s.get('flip_horizontal', False))
        self.flip_v_checkbox.setChecked(s.get('flip_vertical', False))
        rot_idx = {0: 0, 90: 1, 180: 2, 270: 3}.get(s.get('rotation', 0), 0)
        self.rotation_combo.setCurrentIndex(rot_idx)
        self.test_pattern_checkbox.setChecked(s.get('test_pattern', False))
        mode_idx = ['Auto', 'Mode 0: 4056x3040 (Full)', 'Mode 1: 2028x1520 (2x2 binned)', 
                    'Mode 2: 1332x990 (Cropped)'].index(s.get('sensor_mode', 'Auto')) if s.get('sensor_mode', 'Auto') in ['Auto', 'Mode 0: 4056x3040 (Full)', 'Mode 1: 2028x1520 (2x2 binned)', 'Mode 2: 1332x990 (Cropped)'] else 0
        self.sensor_mode_combo.setCurrentIndex(mode_idx)
    
    def _get_settings_from_ui(self) -> dict:
        """Collect current settings from UI widgets"""
        settings = {
            # Exposure
            'brightness': self.brightness_slider.value(),
            'contrast': self.contrast_slider.value(),
            'exp_compensation': self.exp_comp_slider.value(),
            'iso_auto': self.iso_auto_checkbox.isChecked(),
            'iso': self.iso_slider.value(),
            'shutter_auto': self.shutter_auto_checkbox.isChecked(),
            'shutter_us': self.shutter_spin.value(),
            'agc_enabled': self.agc_checkbox.isChecked(),
            
            # Color
            'saturation': self.saturation_slider.value(),
            'wb_mode': self.wb_combo.currentText(),
            'color_temp': self.color_temp_spin.value(),
            'manual_gains': self.manual_gains_checkbox.isChecked(),
            'red_gain': self.red_gain_spin.value(),
            'blue_gain': self.blue_gain_spin.value(),
            'grayscale': self.grayscale_checkbox.isChecked(),
            
            # Processing
            'sharpness': self.sharpness_slider.value(),
            'denoise_mode': self.denoise_combo.currentText(),
            'lens_shading': self.lens_shading_checkbox.isChecked(),
            'hdr_enabled': self.hdr_checkbox.isChecked(),
            
            # Focus/Crop
            'zoom_enabled': self.zoom_enabled_checkbox.isChecked(),
            'zoom_level': self.zoom_slider.value(),
            'crop_enabled': self.crop_enabled_checkbox.isChecked(),
            'crop_x': self.crop_x_spin.value(),
            'crop_y': self.crop_y_spin.value(),
            'crop_width': self.crop_w_spin.value(),
            'crop_height': self.crop_h_spin.value(),
            
            # Capture
            'jpeg_quality': self.quality_slider.value(),
            'raw_enabled': self.raw_enabled_checkbox.isChecked() if self._is_raw_capable() and hasattr(self, 'raw_enabled_checkbox') else False,
            'exif_enabled': self.exif_checkbox.isChecked(),
            'timestamp_filename': self.timestamp_checkbox.isChecked(),
            
            # Advanced
            'fps': self.fps_spin.value(),
            'flip_horizontal': self.flip_h_checkbox.isChecked(),
            'flip_vertical': self.flip_v_checkbox.isChecked(),
            'rotation': [0, 90, 180, 270][self.rotation_combo.currentIndex()],
            'test_pattern': self.test_pattern_checkbox.isChecked(),
            'sensor_mode': self.sensor_mode_combo.currentText(),
        }
        return settings
    
    def _apply_settings(self):
        """Apply settings to camera and save"""
        settings = self._get_settings_from_ui()
        
        # Save to file
        self._save_settings(settings)
        self.settings = settings
        
        # Emit signal for network manager to send to camera
        self.settings_changed.emit(self.ip, settings)
        
        logger.info(f"[OPTIONS] Settings applied for {self.camera_name}")
        self.accept()
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self._get_default_settings()
        self._load_values_to_ui()
        logger.info(f"[OPTIONS] Settings reset to defaults for {self.camera_name}")
