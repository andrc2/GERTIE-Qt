# GERTIE Qt Migration - Session Recovery Prompt

**Use this prompt to resume development in a new conversation if timeout occurs**

---

## Current State (2025-11-20 15:35)

### Project Location
`/Users/andrew1/Desktop/camera_system_qt_conversion/`

### What's Complete

**Phase 0**: ✅ Project structure, documentation, reference code
**Phase 1**: ✅ PySide6 selected (2x faster than PyQt6, benchmarked)
**Phase 2**: ✅ 30 FPS validated with 8-camera mock system
**Phase 3**: 🟡 50% complete
  - ✅ NetworkManager (QThread, UDP commands)
  - ✅ Still capture functionality (per-camera + batch)
  - ✅ Gallery system with auto-refresh thumbnails
  - ✅ Integrated UI with splitter layout
  - ⏳ Camera settings dialog (IN PROGRESS)

### Current Work
Building camera settings dialog to control:
- Brightness, contrast, saturation
- ISO, shutter speed, exposure mode
- White balance
- JPEG quality
- Matching Tkinter protocol exactly

### Git Status
- Latest commit: 247092a
- Branch: master
- Working directory: Clean
- Files: 2,897 lines Qt code

### Test Results
All automated tests passing:
- Phase 1: PyQt6 vs PySide6 benchmark → PySide6 wins
- Phase 2: 30 FPS performance test → 30.5 FPS achieved
- Phase 3: Gallery system test → 21/21 images correct

---

## Resume Instructions

### Step 1: Verify Context
```bash
cd ~/Desktop/camera_system_qt_conversion
git log --oneline -5
git status
ls src/*.py
```

### Step 2: Check Session Logs
Read last 100 lines of session log:
```bash
DC: read_file path="/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md" offset=-100
DC: read_file path="/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt" offset=-100
```

### Step 3: Review Reference Code
Check Tkinter camera settings for protocol compatibility:
```bash
DC: read_file path="/Users/andrew1/Desktop/camera_system_integrated_final/master/camera_gui/dialogs/camera_settings.py" offset=0 length=150
```

### Step 4: Continue Development
Say: "Continue Phase 3 Option A - build camera settings dialog matching Tkinter protocol"

---

## Critical Compatibility Requirements

### Network Protocol (UDP Port 6000)
Commands must match Tkinter format exactly:

**Settings Package** (bulk update):
```
SET_ALL_SETTINGS_{"brightness":0,"contrast":50,"iso":100,...}
```

**Individual Settings**:
```
SET_CAMERA_BRIGHTNESS_0
SET_CAMERA_CONTRAST_50
SET_CAMERA_ISO_100
SET_CAMERA_SHUTTER_SPEED_1000
SET_CAMERA_WHITE_BALANCE_auto
```

### Settings Values (Must Match Tkinter)
- **brightness**: -50 to +50 (GUI scale), 0 = neutral → converts to -1.0 to +1.0 for libcamera
- **contrast**: 0-100 (50 = neutral)
- **saturation**: 0-100 (50 = neutral)
- **iso**: 100-6400
- **shutter_speed**: microseconds (100-1000000)
- **jpeg_quality**: 1-100 (95 = default for stills)
- **white_balance**: auto/daylight/cloudy/tungsten/fluorescent/incandescent/flash/horizon
- **exposure_mode**: auto/manual/night/sports/snow/beach/verylong/fixedfps

### High-Resolution Capture
- Video preview: 640x480
- Still capture: 4608x2592 (full HQ sensor)
- NO --width/--height in libcamera-still (lets it default to high-res)
- JPEG quality: 95% for stills

### Transform Controls (Future Phase 3)
- crop_enabled: bool
- crop_x, crop_y, crop_width, crop_height: integers
- flip_horizontal, flip_vertical: bool
- rotation: 0/90/180/270
- grayscale: bool

---

## File Structure Reference

### Source Files (src/)
- `mock_camera.py` (399 lines) - 8-camera mock system
- `camera_grid.py` (203 lines) - Basic grid (Phase 2)
- `network_manager.py` (196 lines) - UDP communication
- `camera_grid_with_capture.py` (378 lines) - Grid + capture
- `gallery_panel.py` (265 lines) - Gallery display
- `gertie_qt.py` (352 lines) - Integrated main application
- `test_*.py` - Various automated tests

### Reference Files (reference_tkinter/)
- `still_capture.py` (1,022 lines) - Pi camera settings handler
- `video_stream.py` - Video streaming protocol
- Look here for exact protocol implementation

### Documentation (docs/)
- `MACBOOK_TESTING_PROTOCOL.txt`
- `QT_CONVERSION_PROTOCOL.txt`

---

## Development Approach

### Always Use:
1. Desktop Commander for ALL file operations
2. Mock mode for MacBook testing (no Pi needed)
3. Automated tests for validation
4. Git commits after each feature
5. Session logging after every action

### Session Logging
Update after EVERY action:
- `/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt`
- `/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md`

### Testing Strategy
1. Build feature
2. Create automated test
3. Run test, verify results
4. Commit if passing
5. Update logs

---

## Next Tasks (Camera Settings Dialog)

### What to Build
1. **CameraSettingsDialog** class (PySide6 QDialog)
   - Sliders for brightness, contrast, saturation, ISO
   - Spinbox for shutter speed
   - Dropdown for white balance
   - Dropdown for exposure mode
   - Spinbox for JPEG quality
   - Apply/Reset/Close buttons

2. **Integration**
   - Add "Settings" button to each camera widget
   - Send settings via NetworkManager
   - Support both individual and bulk updates
   - Settings persistence (JSON file)

3. **Testing**
   - Automated test: open dialog, change settings, verify commands sent
   - Verify settings format matches Tkinter protocol exactly

---

## Success Criteria

### For Camera Settings Dialog
- ✅ Dialog opens and displays current settings
- ✅ All controls functional (sliders, dropdowns, spinboxes)
- ✅ Sends correct UDP command format
- ✅ Matches Tkinter protocol exactly
- ✅ Automated test passes
- ✅ Git committed

### For Overall Phase 3
- ✅ Still capture working
- ✅ Gallery system working
- ✅ Camera settings working ← CURRENT
- ⏳ Transform controls (crop/rotate/flip)
- ⏳ Real network mode (Pi hardware)
- ⏳ Error handling
- ⏳ Full-size image viewer

---

## Important Notes

### Mock Mode vs Real Mode
- Current: mock_mode=True (for MacBook testing)
- Future: mock_mode=False (for Pi deployment)
- NetworkManager supports both seamlessly

### Original System Compatibility
The Qt system MUST be compatible with:
- Existing Pi camera scripts (still_capture.py, video_stream.py)
- UDP command protocol on port 6000
- Settings format and value ranges
- Transform pipeline (shared/transforms.py)
- High-resolution capture (4608x2592)
- Gallery storage location

### Performance Targets
- GUI: 30 FPS ✓ (currently 29.7-30.5 FPS)
- Captures: <100ms response time
- Settings updates: <200ms
- Gallery refresh: 1s intervals
- No UI blocking ever (QThread for everything)

---

## Quick Commands for Resume

```bash
# Check current state
cd ~/Desktop/camera_system_qt_conversion && git status && git log -1

# Read session logs
tail -100 ~/Desktop/QT_CONVERSION_LOG.txt

# List source files
ls -lh ~/Desktop/camera_system_qt_conversion/src/*.py

# Run latest test
cd ~/Desktop/camera_system_qt_conversion/src && python3 test_gallery_auto.py

# Check captures
ls ~/Desktop/camera_system_qt_conversion/src/mock_captures/ | wc -l
```

---

## Contact Recovery Prompt

**Copy this into a new conversation:**

```
I'm continuing GERTIE Qt migration development. We were working on Phase 3 
camera settings dialog. Please read the recovery context:

DC: read_file path="/Users/andrew1/Desktop/camera_system_qt_conversion/docs/SESSION_RECOVERY.md"

Then verify current state:
DC: read_file path="/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md" offset=-100
DC: read_file path="/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt" offset=-100

And continue building the camera settings dialog matching the Tkinter protocol 
exactly. Use hands-off automated approach with full testing.
```

---

**Last Updated**: 2025-11-20 15:35
**Phase**: 3 (50% complete)
**Next**: Camera settings dialog
**Status**: Ready to resume
