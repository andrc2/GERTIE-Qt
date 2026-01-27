# GERTIE Qt Conversion - Complete Requirements & Issues

**Last Updated**: 2026-01-27
**Purpose**: Mandatory reference for ALL GERTIE sessions
**Rule**: Read this document at the start of EVERY session to ensure no omissions

---

## ⚡ ABSOLUTE PRIORITIES (Never Compromise)

### Priority 1: PERFORMANCE & RESPONSIVENESS
**This is the HIGHEST priority for all development work.**
- GUI must remain smooth and responsive at all times
- No lag, freezing, or sluggish behavior
- Video preview must update fluidly (~20+ FPS target)
- User interactions (clicks, keypresses) must respond instantly
- Background operations must NOT block the main thread
- If a feature causes performance degradation, fix performance FIRST

### Priority 2: CORE FUNCTIONALITY PRESERVATION
**These features MUST always work - never break them:**
- High-resolution JPEG capture (4608×2592 from all 8 cameras)
- 8-camera simultaneous video preview
- Instant thumbnail generation on capture
- Gallery with image viewing/navigation/deletion
- Settings persistence across sessions
- Network communication with all slaves

### Priority 3: WYSIWYG (What You See Is What You Get)
**Preview must EXACTLY match final capture:**
- Camera settings reflected in live preview
- Crop region shown in preview = crop in final image
- Brightness, contrast, ISO visible in preview before capture

---

## 🔧 PROJECT CONTEXT

**IMPORTANT**: All GERTIE development is now Qt conversion ONLY.
- **Active Project**: `GERTIE_Qt` (`~/Desktop/GERTIE_Qt`)
- **Reference Only**: `GERTIE_Tkinter` (for feature parity, NOT being developed)
- **Assumption**: Any GERTIE work request = Qt conversion project
- **Deployment**: Via `sync_to_slaves.sh` to 8 Raspberry Pi cameras

**Do NOT modify GERTIE_Tkinter** - it is reference material only.

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

### C3: Keyboard Shortcuts ~~Differ from Tkinter (Wrong Behavior)~~
**Status**: ✅ FIXED (2026-01-27)

| Key | Qt Behavior | Matches Tkinter? |
|-----|-------------|------------------|
| **Space** | Capture All | ✅ |
| **C** | Capture All | ✅ |
| **1-8** | Toggle camera preview (exclusive mode) | ✅ |
| **R** | Restart all streams | ✅ |
| **Escape** | Show all cameras (exit exclusive) | ✅ |
| **S** | Open settings panel | ✅ |
| **G** | Toggle gallery | ✅ |
| **Q** | Quit | ✅ |

**Exclusive Mode (1-8 keys)**:
- Pressing 1-8 enlarges that camera to fill the grid (hides others) ✅
- Pressing same key again OR Escape returns to normal 8-camera grid ✅
- Debouncing prevents rapid switching (300ms cooldown) ✅
- Resolution switching to HD mode for focus checking ✅

---

### C4: WYSIWYG Aspect Ratio Mismatch
**Status**: POTENTIALLY BROKEN (needs verification)
**Issue**: Preview and capture may have different aspect ratios

| Component | Resolution | Aspect Ratio |
|-----------|------------|--------------|
| Video Preview | 640×480 | 4:3 |
| Sensor/Capture | 4608×2592 | 16:9 |

**Impact**: What user sees in preview may NOT match final captured image
**Required Fix**: 
- Either match preview to 16:9 (640×360 or 854×480)
- OR crop capture to match 4:3 preview
- User must see EXACTLY what they will capture

---

### C5: Low FPS Performance
**Status**: OBSERVED (8.6 FPS in testing, should be ~20)
**Impact**: Sluggish preview, harder to verify focus
**Possible Causes**:
- JPEG decode overhead on main thread
- Network congestion with 8 streams
- GUI update frequency

**Note**: This was partially addressed but may need further optimization

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

### M2: Individual Camera Capture (Separate from Toggle)
**Status**: NOT IMPLEMENTED
**Issue**: 1-8 keys will be for toggle preview, need separate capture method
**Required Features**:
- [ ] "Capture" button in each camera widget (already exists but broken)
- [ ] OR right-click context menu → Capture
- [ ] OR Ctrl+1-8 for individual capture
- [ ] Must create hi-res JPEG on slave
- [ ] Must add thumbnail to gallery
- [ ] Must show capture feedback (flash, sound)

---

### M3: Audio Feedback
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Shutter sound on capture
- [ ] Volume control in preferences
- [ ] Enable/disable toggle
- [ ] Use existing shutter.wav file

**Reference**: `GERTIE_Tkinter/master/camera_gui/utils/audio_feedback.py`

---

### M4: Visual Status Indicators
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Heartbeat status dots per camera (🟢 online, 🔴 offline, 🟡 idle)
- [ ] State labels per camera (IDLE/STREAMING/CAPTURING)
- [ ] Connection quality indicator

**Reference**: `GERTIE_Tkinter/master/camera_gui/widgets/camera_frame.py`

---

### M5: Menu Bar System
**Status**: NOT IMPLEMENTED
**Required Menus**:
- [ ] File menu (Exit)
- [ ] Settings menu (Camera settings, Device naming, Preferences)
- [ ] System menu (Restart/Shutdown controls)
- [ ] Help menu (Shortcuts reference)

---

### M6: Device Naming Dialog
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Custom names for each camera (rep1 → "Dorsal", etc.)
- [ ] Persistent storage of names
- [ ] Names displayed in camera frames

**Reference**: `GERTIE_Tkinter/master/camera_gui/dialogs/device_naming.py`

---

### M7: App Preferences Dialog
**Status**: NOT IMPLEMENTED
**Required Features**:
- [ ] Audio enable/disable
- [ ] Auto-save settings
- [ ] Default capture directory
- [ ] Preview quality settings

---

### M8: Keyboard Shortcuts Help Bar
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

**REMEMBER**: Performance is ALWAYS the highest priority. If implementing a feature causes lag or sluggishness, fix the performance issue BEFORE continuing.

### Phase 1: Fix Critical Bugs (Performance-Safe)
1. Fix keyboard shortcuts (Space=Capture, 1-8=Toggle, R=Restart, Escape=ShowAll, S=Settings)
2. Fix individual camera capture (button + separate shortcut)
3. Fix brightness/ISO settings (verify no performance impact)

### Phase 2: System Controls
4. Add restart all streams function
5. Add restart/shutdown individual device
6. Add restart/shutdown all devices
7. Create System menu in menu bar

### Phase 3: WYSIWYG Tools (Performance-Critical)
8. Create visual drag-based crop tool (must not lag)
9. Ensure all camera settings reflect in preview (without frame drops)
10. Debug and fix all camera controls

### Phase 4: Polish
11. Add audio feedback (non-blocking)
12. Add status indicators (lightweight updates only)
13. Add device naming dialog
14. Add app preferences dialog
15. Add shortcuts help bar

### Performance Checkpoints
**After EVERY feature implementation:**
- [ ] Verify FPS remains ≥15 (target ≥20)
- [ ] Verify no GUI freezing or lag
- [ ] Verify capture still works (8/8 cameras)
- [ ] Verify thumbnails still instant
- [ ] Test with rapid repeated actions

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

**Note**: These are READ-ONLY references. Do NOT modify Tkinter code.

---

## 🚀 PERFORMANCE GUIDELINES

### What Causes Lag (AVOID):
- JPEG decoding on main thread (use background threads)
- Blocking network calls (use async/queued)
- Creating/destroying widgets repeatedly (reuse widgets)
- Large memory allocations during frame updates
- Synchronous file I/O during video playback
- Excessive logging/printing during frame processing

### What Keeps It Fast (DO):
- Decode frames in background, display on main thread
- Use dirty flags to skip unnecessary updates
- Pre-allocate buffers and reuse them
- Batch UI updates (don't update 8 cameras 30× each per second)
- Use Qt's built-in scaling (setScaledContents) over manual scaling
- Keep main thread event loop responsive

### Performance Red Flags:
- FPS drops below 10 → STOP and fix immediately
- GUI freezes for >100ms → STOP and fix immediately  
- Mouse/keyboard lag → STOP and fix immediately
- Memory usage climbing → investigate leaks

### Known Performance Decisions:
- Using `setScaledContents(True)` for video (may stretch slightly, but avoids 240 scale ops/sec)
- Decoding frames immediately on receive (keeps decoded_frames ready for instant thumbnails)
- Timer-based frame updates at 20Hz (not per-frame callbacks)

---

## ⚠️ SESSION PROTOCOL REMINDER

**At the start of EVERY GERTIE session:**
1. Read this document completely (especially ⚡ ABSOLUTE PRIORITIES)
2. Check which items are still outstanding
3. Update session log with current focus
4. Do NOT skip items or assume they are done
5. Test features on hardware before marking complete

**Key Reminders:**
- GERTIE = Qt conversion project (never Tkinter)
- Tkinter is REFERENCE ONLY for feature parity
- Performance is ALWAYS the highest priority
- Never break: hi-res capture, video preview, thumbnails, responsiveness
- All development in `~/Desktop/GERTIE_Qt`
- All deployment via `sync_to_slaves.sh`

---

**END OF REQUIREMENTS DOCUMENT**

---

## 📊 CURRENT SESSION STATUS (Update Each Session)

**Last Session**: 2026-01-19
**Last Commit**: 43c4c8e (expanded requirements)
**USB Synced**: ✅
**GitHub Synced**: ✅

### What Was Accomplished This Session:
1. Fixed instant thumbnails (reverted lazy decode) - Commit fcb9f4a
2. Added automatic time sync from control1 RTC - Commit 4ba6833
3. Created this requirements document - Commit 7496129
4. Verified 4 consecutive capture batches work (32 captures, 0 timeouts)

### Current System State:
- Capture All (C key): ✅ WORKING
- Individual Capture: ❌ BROKEN
- Keyboard shortcuts: ❌ WRONG MAPPING
- Brightness/ISO: ❌ NOT WORKING
- Time sync: ✅ WORKING (added this session)
- FPS: ⚠️ 8.6 (lower than ideal)

### Next Session Should Start With:
1. Read this entire document
2. Read session log: `~/Desktop/GERTIE_SESSION_LOG.md` (last 100 lines)
3. Check git status: `cd ~/Desktop/GERTIE_Qt && git log -1 --oneline`
4. Begin with Phase 1: Fix Critical Bugs (keyboard shortcuts first)

### Hardware Testing Needed:
- [ ] Verify brightness settings work after fix
- [ ] Verify ISO settings work after fix
- [ ] Test individual capture after fix
- [ ] Test keyboard shortcuts after fix
- [ ] Test restart/shutdown functions after implementation
