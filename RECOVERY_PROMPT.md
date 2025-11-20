# GERTIE Qt Development - Recovery Prompt

**Use this prompt if the session times out or disconnects:**

---

I'm continuing GERTIE Qt development. Here's where we left off:

**Project**: `/Users/andrew1/Desktop/camera_system_qt_conversion`
**Session Log**: `/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt`
**Main Log**: `/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md`

**Current Phase**: Phase 3 - Camera Settings Dialog (Option A)
**Last Commit**: Check with: `cd ~/Desktop/camera_system_qt_conversion && git log -1 --oneline`

**What We're Building**:
Camera settings dialog compatible with original Tkinter system that controls:
- ISO (100-6400)
- Exposure/Shutter Speed (microseconds)
- Brightness (-50 to +50, GUI scale)
- Contrast (0-100, 50=neutral)
- Saturation (0-100, 50=neutral)
- White Balance (auto/daylight/cloudy/tungsten/etc)
- JPEG Quality (1-100, 95 default for stills)

**Original Reference**: `/Users/andrew1/Desktop/camera_system_integrated_final/master/camera_gui/dialogs/camera_settings.py`

**Requirements**:
1. Must send settings via NetworkManager as "SET_ALL_SETTINGS_{json}" command
2. Must match original brightness conversion: GUI scale (-50 to +50) where 0=neutral
3. Settings sent to port 6000 (still_capture.py listens on this port)
4. Must forward to port 5004 for video_stream.py
5. Must work with libcamera-still high-resolution capture
6. Per-camera settings storage

**Development Protocol**:
- Work in small chunks (10-15 min max)
- Commit after EVERY functional piece
- Update QT_CONVERSION_LOG.txt after EVERY action
- Test each piece before moving to next

**Recovery Steps**:
1. Read last 100 lines of QT_CONVERSION_LOG.txt: `DC: read_file path="/Users/andrew1/Desktop/QT_CONVERSION_LOG.txt" offset=-100`
2. Check git status: `cd ~/Desktop/camera_system_qt_conversion && git status -s && git log -3 --oneline`
3. Continue from last logged action

**Next Actions** (in order):
1. Read original camera_settings.py from Tkinter reference
2. Create camera_settings_dialog.py (start with UI layout only)
3. Test and commit
4. Add signal connections
5. Test and commit
6. Add NetworkManager integration
7. Test and commit
8. Create automated test
9. Final commit

**Critical Compatibility Notes**:
- Brightness: GUI uses -50 to +50 scale, libcamera uses -1.0 to +1.0
- Conversion: `libcamera_brightness = gui_brightness / 50.0`
- Settings format: JSON dict matching camera_settings from still_capture.py
- Network: UDP to IP:6000, command: "SET_ALL_SETTINGS_{json_string}"

**Safety Features Active**:
- Small atomic commits every 10-15 minutes
- Continuous session logging
- Git history preserved
- All work in mock mode (no Pi needed)

Please continue with camera settings dialog development, following the protocol above.

---

**Generated**: 2025-11-20 15:35
**Valid Until**: Project completion
