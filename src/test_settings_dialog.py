#!/usr/bin/env python3
"""
Test camera settings dialog with Apply functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from camera_settings_dialog import CameraSettingsDialog


def test_settings_dialog():
    """Test dialog with apply functionality"""
    print("="*60)
    print("Camera Settings Dialog - Functionality Test (Part 2)")
    print("="*60)
    
    app = QApplication(sys.argv)
    
    dialog = CameraSettingsDialog("192.168.0.201", "REP1")
    
    # Connect signal to verify it works
    def on_settings_applied(ip, settings):
        print(f"\n✓ Signal received!")
        print(f"  IP: {ip}")
        print(f"  Settings: {settings}")
    
    dialog.settings_applied.connect(on_settings_applied)
    
    # Show dialog
    result = dialog.exec()
    
    print(f"\nDialog result: {'Applied' if result else 'Cancelled'}")
    
    # Check if settings file was created
    settings_file = dialog.get_settings_filename()
    if os.path.exists(settings_file):
        print(f"✓ Settings file created: {settings_file}")
        with open(settings_file, "r") as f:
            import json
            saved = json.load(f)
            print(f"  ISO: {saved['iso']}")
            print(f"  Brightness: {saved['brightness']}")
    else:
        print("✗ Settings file not found (user cancelled)")
    
    return 0


if __name__ == "__main__":
    sys.exit(test_settings_dialog())
