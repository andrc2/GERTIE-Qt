# GERTIE Qt Conversion - Complete Requirements & Issues

**Last Updated**: 2026-01-19
**Purpose**: Mandatory reference for ALL Qt conversion sessions
**Rule**: Read this document at the start of EVERY session to ensure no omissions

---

## 🔴 CRITICAL ISSUES (Broken/Non-Functional)

### C1: Individual Camera Capture Does Not Work
**Status**: BROKEN
**Symptoms**:
- Pressing 1-8 keys does NOT create actual hi-res captures
- Pressing 1-8 keys does NOT create thumbnails in gallery
- Individual "Capture" button in camera widget does NOT capture
- Only "Capture All" (C key) works for actual captures

**Required Fix**:
- Implement working individual camera capture
- Must trigger hi-res JPEG capture on slave
- Must create thumbnail in gallery
- Must show progress indicator

---

### C2: Brightness and ISO Settings Do Not Work
**Status**: BROKEN
**Symptoms**:
- Adjusting brightness in settings dialog has no visible effect
- Adjusting ISO in settings dialog has no visible effect
- Settings may be sent but not applied correctly on slave

**Required Fix**:
- Debug settings transmission to slave
- Verify slave receives and applies settings
- Ensure video preview reflects settings changes
- Ensure hi-res capture uses same settings

---

### C3: Keyboard Shortcuts Differ from Tkinter (Wrong Behavior)
**Status**: INCORRECT IMPLEMENTATION

| Key | Current Qt Behavior | Required Behavior (Match Tkinter) |
|-----|---------------------|-----------------------------------|
| **Space** | Pause/Resume video | **Capture All** |
| **1-8** | Capture individual (broken) | **Toggle camera preview** (show single camera fullscreen) |
| **R** | Reset stats | **Restart all streams** |
| **C** | Capture All | Keep as-is (additional shortcut) |
| **Escape** | Not implemented | **Show all cameras** (exit single-camera view) |
| **S** | Not implemented | **Open settings panel** |

---

## 🟡 MISSING FEATURES (Feature Parity with Tkinter)

### M1: System Control Functions
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Restart all video streams
- [ ] Restart individual camera stream (rep1-rep8)
- [ ] Shutdown individual device (rep1-rep8)
- [ ] Shutdown all devices
- [ ] Reboot individual device
- [ ] Reboot all devices

**Implementation**: Menu bar → System Controls menu (like Tkinter)

---

### M2: Audio Feedback
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Shutter sound on capture
- [ ] Volume control in preferences
- [ ] Enable/disable toggle
- [ ] Use existing shutter.wav file

**Reference**: `GERTIE_Tkinter/master/camera_gui/utils/audio_feedback.py`

---

### M3: Visual Status Indicators
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Heartbeat status dots per camera (🟢 online, 🔴 offline, 🟡 idle)
- [ ] State labels per camera (IDLE/STREAMING/CAPTURING)
- [ ] Connection quality indicator

**Reference**: `GERTIE_Tkinter/master/camera_gui/widgets/camera_frame.py`

---

### M4: Menu Bar System
**Status**: NOT IMPLEMENTED
**Required Menus**:
- [ ] File menu (Exit)
- [ ] Settings menu (Camera settings, Device naming, Preferences)
- [ ] System menu (Restart/Shutdown controls)
- [ ] Help menu (Shortcuts reference)

---

### M5: Device Naming Dialog
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Custom names for each camera (rep1 → "Dorsal", etc.)
- [ ] Persistent storage of names
- [ ] Names displayed in camera frames

**Reference**: `GERTIE_Tkinter/master/camera_gui/dialogs/device_naming.py`

---

### M6: App Preferences Dialog
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Audio enable/disable
- [ ] Auto-save settings
- [ ] Default capture directory
- [ ] Preview quality settings

---

### M7: Keyboard Shortcuts Help Bar
**Status**: NOT IMPLEMENTED
**Required**: Display shortcuts at bottom of window:
```
Shortcuts: [Space] Capture All | [1-8] Focus Camera | [Esc] Show All | [S] Settings | [G] Gallery | [R] Restart | [Q] Quit
```

---

## 🔵 NEW FEATURES REQUIRED

### N1: Visual Drag-Based Crop Tool (WYSIWYG)
**Status**: NOT IMPLEMENTED
**Priority**: HIGH

**Requirements**:
1. **Access**: From camera settings dialog or dedicated menu
2. **Preview**: Display current video frame as static image
3. **Interaction**: Drag rectangle to define crop region
4. **Handles**: Resize handles on corners and edges
5. **Real-time feedback**: Show crop dimensions (X, Y, W, H) as user drags
6. **WYSIWYG Critical**: 
   - Video preview MUST show cropped view after applying
   - Hi-res capture MUST use identical crop region (scaled to sensor)
   - What user sees in preview = what they get in final image
7. **Aspect ratio lock**: Optional lock to maintain aspect ratio
8. **Reset button**: Return to full sensor view

**Technical Notes**:
- Preview resolution: 640×480 (or current stream resolution)
- Sensor resolution: 4608×2592
- Crop coordinates must scale proportionally between preview and sensor
- Formula: `sensor_coord = preview_coord * (4608/640)` for X, `(2592/480)` for Y

---

### N2: Advanced Camera Settings Dialog (WYSIWYG)
**Status**: PARTIALLY IMPLEMENTED (settings exist but don't work)
**Priority**: HIGH

**Required Controls** (all must reflect in live preview AND final capture):

| Setting | Range | Current Status |
|---------|-------|----------------|
| **Brightness** | -100 to +100 | ❌ Not working |
| **Contrast** | 0 to 100 | ⚠️ Untested |
| **ISO** | 100 to 6400 | ❌ Not working |
| **Shutter Speed** | 1μs to 1s | ⚠️ Untested |
| **White Balance** | Auto/Daylight/Cloudy/Tungsten/etc | ⚠️ Untested |
| **Saturation** | 0 to 100 | ⚠️ Untested |
| **Exposure Compensation** | -3 to +3 EV | ⚠️ Untested |

**WYSIWYG Requirements**:
- Video stream preview MUST update in real-time when settings change
- Hi-res capture MUST use identical settings
- No difference between preview appearance and final image (within resolution limits)

**Debug Steps**:
1. Verify settings are sent to slave (`SET_ALL_SETTINGS_` command)
2. Verify slave receives and parses settings correctly
3. Verify slave applies settings to Picamera2
4. Verify settings apply to both video stream AND still capture

---

## ✅ WORKING FEATURES (Verified)

- [x] 8-camera video preview grid
- [x] Capture All (C key) - creates 8 hi-res JPEGs
- [x] Instant thumbnails from video frames
- [x] Gallery with scroll navigation
- [x] Image viewer (enlarge, navigate, delete, open folder)
- [x] Toggle gallery (G key)
- [x] Quit (Q key)
- [x] Progress bar with X/Y counter
- [x] Resizable gallery (splitter)
- [x] Automatic time sync on launch (control1 RTC → slaves)
- [x] Slave capture lock (prevents collision)
- [x] Transform settings UI (flip H/V, rotation) - UI exists
- [x] Crop settings UI (X/Y/W/H) - UI exists, needs visual tool

---

## 📋 IMPLEMENTATION PRIORITY ORDER

### Phase 1: Fix Critical Bugs
1. Fix brightness/ISO settings not working
2. Fix individual camera capture
3. Fix keyboard shortcuts (Space=Capture, 1-8=Toggle, R=Restart)

### Phase 2: System Controls
4. Add restart all streams function
5. Add restart/shutdown individual device
6. Add restart/shutdown all devices
7. Create System menu in menu bar

### Phase 3: WYSIWYG Tools
8. Create visual drag-based crop tool
9. Ensure all camera settings reflect in preview
10. Debug and fix all camera controls

### Phase 4: Polish
11. Add audio feedback
12. Add status indicators (heartbeat, state)
13. Add device naming dialog
14. Add app preferences dialog
15. Add shortcuts help bar

---

## 🔧 TECHNICAL REFERENCE

### Slave Command Protocol
```
START_STREAM          - Start video streaming
STOP_STREAM           - Stop video streaming
RESTART_STREAM_WITH_SETTINGS - Restart with new settings
CAPTURE_STILL         - Capture hi-res JPEG
SET_ALL_SETTINGS_{json} - Apply camera settings
SET_FLIP_HORIZONTAL_{bool}
SET_FLIP_VERTICAL_{bool}
SET_ROTATION_{degrees}
REBOOT                - Reboot device
sudo poweroff         - Shutdown device
```

### Key Files
- GUI: `src/gertie_qt.py`
- Network: `src/network_manager.py`
- Settings Dialog: `src/camera_settings_dialog.py`
- Gallery: `src/gallery_panel.py`
- Slave Capture: `slave/still_capture.py`
- Slave Video: `slave/video_stream.py`

### Tkinter Reference Files
- Main GUI: `GERTIE_Tkinter/master/camera_gui/core/gui_base.py`
- Camera Frame: `GERTIE_Tkinter/master/camera_gui/widgets/camera_frame.py`
- Settings Menu: `GERTIE_Tkinter/master/camera_gui/menu/settings_menu.py`
- System Menu: `GERTIE_Tkinter/master/camera_gui/menu/system_menu.py`
- Audio: `GERTIE_Tkinter/master/camera_gui/utils/audio_feedback.py`

---

## ⚠️ SESSION PROTOCOL REMINDER

**At the start of EVERY Qt conversion session:**
1. Read this document completely
2. Check which items are still outstanding
3. Update session log with current focus
4. Do NOT skip items or assume they are done
5. Test features on hardware before marking complete

---

**END OF REQUIREMENTS DOCUMENT**
