#!/usr/bin/env python3
"""
Automated test for Camera Settings Dialog
Fully hands-off validation:
1. Opens settings dialog programmatically
2. Changes settings values
3. Applies settings
4. Verifies settings saved to file
5. Reports results
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer
from camera_settings_dialog import CameraSettingsDialog


def run_automated_settings_test():
    """Run fully automated settings dialog test"""
    print("="*70)
    print("GERTIE Qt - Automated Camera Settings Test")
    print("="*70)
    print("Test Plan:")
    print("  1. Create settings dialog for camera 1")
    print("  2. Modify all settings programmatically")
    print("  3. Apply settings")
    print("  4. Verify settings saved to JSON")
    print("  5. Verify settings can be loaded back")
    print("="*70)
    
    app = QApplication(sys.argv)
    
    test_results = {
        'dialog_created': False,
        'settings_modified': False,
        'settings_applied': False,
        'file_saved': False,
        'settings_reloaded': False,
        'values_match': False
    }
    
    # Test settings
    test_settings = {
        'iso': 800,
        'brightness': 25,
        'contrast': 75,
        'saturation': 60,
        'flip_horizontal': True,
        'flip_vertical': False,
        'grayscale': True,
        'rotation': 90
    }
    
    print("\n1. Creating settings dialog...")
    camera_id = 1
    ip = "192.168.0.201"
    dialog = CameraSettingsDialog(camera_id, ip)
    test_results['dialog_created'] = True
    print("  ✓ Dialog created")
    
    print("\n2. Modifying settings programmatically...")
    dialog.iso_slider.setValue(test_settings['iso'])
    dialog.brightness_slider.setValue(test_settings['brightness'])
    dialog.contrast_slider.setValue(test_settings['contrast'])
    dialog.saturation_slider.setValue(test_settings['saturation'])
    dialog.flip_h_checkbox.setChecked(test_settings['flip_horizontal'])
    dialog.flip_v_checkbox.setChecked(test_settings['flip_vertical'])
    dialog.grayscale_checkbox.setChecked(test_settings['grayscale'])
    rotation_index = [0, 90, 180, 270].index(test_settings['rotation'])
    dialog.rotation_combo.setCurrentIndex(rotation_index)
    test_results['settings_modified'] = True
    print("  ✓ Settings modified:")
    for key, value in test_settings.items():
        print(f"    {key}: {value}")
    
    print("\n3. Applying settings...")
    
    # Connect signal to track application
    settings_applied = {'done': False, 'ip': None, 'settings': None}
    
    def on_settings_changed(ip, settings):
        settings_applied['done'] = True
        settings_applied['ip'] = ip
        settings_applied['settings'] = settings
    
    dialog.settings_changed.connect(on_settings_changed)
    
    # Trigger apply (simulates clicking Apply button)
    dialog._apply_settings()
    
    if settings_applied['done']:
        test_results['settings_applied'] = True
        print("  ✓ Settings applied signal received")
    
    # Check if file was saved
    if os.path.exists(dialog.settings_file):
        test_results['file_saved'] = True
        print(f"  ✓ Settings file saved: {dialog.settings_file}")
    else:
        print(f"  ✗ Settings file not found: {dialog.settings_file}")
    
    print("\n4. Verifying settings in file...")
    try:
        with open(dialog.settings_file, 'r') as f:
            saved_settings = json.load(f)
        test_results['settings_reloaded'] = True
        print("  ✓ Settings loaded from file:")
        for key, value in saved_settings.items():
            print(f"    {key}: {value}")
        
        # Check if values match
        all_match = True
        for key, expected_value in test_settings.items():
            actual_value = saved_settings.get(key)
            if actual_value != expected_value:
                all_match = False
                print(f"  ✗ Mismatch: {key} = {actual_value} (expected {expected_value})")
        
        if all_match:
            test_results['values_match'] = True
            print("  ✓ All values match expected settings")
    
    except Exception as e:
        print(f"  ✗ Error reading settings file: {e}")
    
    print("\n5. Testing settings persistence...")
    # Create new dialog to verify settings load correctly
    dialog2 = CameraSettingsDialog(camera_id, ip)
    
    persistence_ok = True
    checks = [
        ('iso', dialog2.iso_slider.value(), test_settings['iso']),
        ('brightness', dialog2.brightness_slider.value(), test_settings['brightness']),
        ('contrast', dialog2.contrast_slider.value(), test_settings['contrast']),
        ('saturation', dialog2.saturation_slider.value(), test_settings['saturation']),
        ('flip_horizontal', dialog2.flip_h_checkbox.isChecked(), test_settings['flip_horizontal']),
        ('grayscale', dialog2.grayscale_checkbox.isChecked(), test_settings['grayscale']),
    ]
    
    for name, actual, expected in checks:
        if actual != expected:
            persistence_ok = False
            print(f"  ✗ {name}: {actual} != {expected}")
    
    if persistence_ok:
        print("  ✓ Settings persistence verified")
    
    # Final report
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"Dialog Created: {'✓' if test_results['dialog_created'] else '✗'}")
    print(f"Settings Modified: {'✓' if test_results['settings_modified'] else '✗'}")
    print(f"Settings Applied: {'✓' if test_results['settings_applied'] else '✗'}")
    print(f"File Saved: {'✓' if test_results['file_saved'] else '✗'}")
    print(f"Settings Reloaded: {'✓' if test_results['settings_reloaded'] else '✗'}")
    print(f"Values Match: {'✓' if test_results['values_match'] else '✗'}")
    print(f"Persistence OK: {'✓' if persistence_ok else '✗'}")
    
    # Determine pass/fail
    success = all([
        test_results['dialog_created'],
        test_results['settings_modified'],
        test_results['settings_applied'],
        test_results['file_saved'],
        test_results['settings_reloaded'],
        test_results['values_match'],
        persistence_ok
    ])
    
    if success:
        print("\n✓ TEST PASSED - Camera settings system working correctly!")
        print("  - Dialog creates successfully")
        print("  - Settings can be modified")
        print("  - Settings save to JSON")
        print("  - Settings persist across sessions")
    else:
        print("\n✗ TEST FAILED - One or more checks failed")
    
    print("="*70)
    
    # Cleanup
    if os.path.exists(dialog.settings_file):
        os.remove(dialog.settings_file)
        print(f"\n✓ Cleaned up test file: {dialog.settings_file}")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = run_automated_settings_test()
    sys.exit(exit_code)
