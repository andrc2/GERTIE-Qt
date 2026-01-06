# GERTIE Qt - Pi Hardware Deployment Instructions
## Phase 3B: Real Network Validation
**Created**: January 6, 2026
**Purpose**: Deploy and test Qt GUI on Raspberry Pi hardware

---

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │     control1 (192.168.0.200)        │
                    │  ┌─────────────────────────────┐    │
                    │  │  GERTIE Qt GUI (NEW)        │    │
                    │  │  - src/gertie_qt.py         │    │
                    │  │  - PySide6 framework        │    │
                    │  └──────────────┬──────────────┘    │
                    │                 │                   │
                    │  ┌──────────────▼──────────────┐    │
                    │  │  rep8 (local camera)        │    │
                    │  │  - Tkinter slave scripts    │    │
                    │  │  - Port 6010 (still)        │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────┬───────────────────┘
                                      │ UDP
                    ┌─────────────────▼───────────────────┐
                    │         PoE Network Switch          │
                    └─┬───┬───┬───┬───┬───┬───┬───────────┘
                      │   │   │   │   │   │   │
              ┌───────▼───▼───▼───▼───▼───▼───▼───────┐
              │  rep1  rep2  rep3  rep4  rep5  rep6  rep7  │
              │  .201  .202  .203  .204  .205  .206  .207  │
              │                                            │
              │  All run Tkinter slave scripts:            │
              │  - video_stream.py (Port 5002)             │
              │  - still_capture.py (Port 6000)            │
              └────────────────────────────────────────────┘
```

**Key Point**: Qt GUI replaces ONLY the Tkinter master GUI on control1. All slave Pis continue running Tkinter slave scripts.

---

## Prerequisites Checklist

Before deployment:

- [ ] USB drive available
- [ ] control1 Pi accessible (SSH or physical)
- [ ] All 8 cameras powered on
- [ ] PoE switch operational
- [ ] Network 192.168.0.x reachable

---

## Deployment Steps

### Step 1: Prepare USB Drive (MacBook)

```bash
# On MacBook - copy Qt project to USB
cp -r ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion /Volumes/USB/
```

**Verify contents**:
```
camera_system_qt_conversion/
├── src/
│   ├── gertie_qt.py          # Main application
│   ├── network_manager.py    # UDP communication
│   ├── config.py             # Network configuration
│   ├── gallery_panel.py      # Gallery system
│   ├── camera_settings_dialog.py
│   ├── image_viewer.py
│   └── mock_camera.py        # For testing
├── docs/
├── reference_tkinter/
├── DEPLOY_NOW.txt
└── README.txt
```

### Step 2: Transfer to control1 (On Pi)

```bash
# Mount USB (if not auto-mounted)
sudo mount /dev/sda1 /media/USB

# Copy Qt project
cp -r /media/USB/camera_system_qt_conversion /home/andrc1/

# Verify
ls -la /home/andrc1/camera_system_qt_conversion/src/
```

### Step 3: Install Dependencies (One-time)

```bash
# On control1 Pi
cd /home/andrc1/camera_system_qt_conversion

# Install PySide6 (Qt framework)
pip3 install PySide6

# Verify installation
python3 -c "from PySide6.QtWidgets import QApplication; print('PySide6 OK')"

# Install Pillow if not present
pip3 install Pillow
```

### Step 4: Ensure Slave Services Running

Before testing Qt, verify slaves are operational:

```bash
# Check all remote slaves (from control1)
for ip in 201 202 203 204 205 206 207; do
    echo "Checking 192.168.0.$ip..."
    ssh andrc1@192.168.0.$ip "systemctl status video_stream.service --no-pager | head -3"
done

# Check local rep8
systemctl status video_stream.service --no-pager | head -3
```

**Expected**: All show "active (running)"

If services not running, restart them:
```bash
# On each slave
sudo systemctl restart video_stream.service
sudo systemctl restart still_capture.service
```

### Step 5: Start Qt GUI

```bash
# On control1 Pi
cd /home/andrc1/camera_system_qt_conversion/src

# Set display (if running via SSH with X forwarding)
export DISPLAY=:0

# Start Qt application with logging
python3 gertie_qt.py 2>&1 | tee /home/andrc1/Desktop/qt_test_$(date +%Y%m%d_%H%M%S).log
```

---

## Testing Protocol

### Test 1: GUI Startup (Mock Mode)
**Expected**: GUI opens with 8 camera panels, status bar shows "Mock Mode"

- [ ] All 8 camera labels visible (REP1-REP8)
- [ ] Gallery panel on right side
- [ ] Status bar at bottom
- [ ] No Python errors in terminal

### Test 2: Switch to Real Network Mode
**Action**: Press `M` key or click mode toggle button

- [ ] Status bar changes to "Real Mode"
- [ ] Heartbeat monitor starts
- [ ] Terminal shows "Starting heartbeat monitoring..."

### Test 3: Heartbeat Detection
**Expected**: Within 5-10 seconds, cameras come online

Watch terminal for:
```
[INFO] Camera 1 (192.168.0.201): Online
[INFO] Camera 2 (192.168.0.202): Online
...
[INFO] Online cameras: [1, 2, 3, 4, 5, 6, 7, 8]
```

- [ ] All 8 cameras detected
- [ ] No timeout errors

### Test 4: Single Camera Capture
**Action**: Click capture button on Camera 1 panel OR press `1` key

- [ ] Terminal shows: "Sending capture to 192.168.0.201:6000"
- [ ] Terminal shows: "Capture command sent successfully"
- [ ] Image appears in gallery (after transfer)

### Test 5: Batch Capture
**Action**: Press `Spacebar`

- [ ] Terminal shows capture commands for all 8 cameras
- [ ] "Batch capture initiated for 8 cameras"
- [ ] Gallery updates with new images

### Test 6: Video Stream Toggle
**Action**: Click Start Stream on Camera 1

- [ ] Terminal shows: "Sending START_STREAM to 192.168.0.201:5004"
- [ ] Video feed appears in camera panel
- [ ] Frame rate ~30 FPS

### Test 7: Settings Dialog
**Action**: Click settings icon on Camera 1

- [ ] Dialog opens with camera IP displayed
- [ ] Sliders functional (brightness, sharpness, etc.)
- [ ] Apply button sends settings to camera

---

## Collecting Results

After testing, collect logs:

```bash
# On control1
# Copy Qt log
cp /home/andrc1/Desktop/qt_test_*.log /media/USB/

# Copy any updatelog
cp /home/andrc1/Desktop/updatelog.txt /media/USB/ 2>/dev/null

# Unmount USB
sudo umount /media/USB
```

Return USB to MacBook and copy logs to:
```
/Users/andrew1/Desktop/GERTIE_WORKSPACE/02_SESSION_LOGS/
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'PySide6'"
**Solution**: Install PySide6
```bash
pip3 install PySide6
```

### Issue: "Cannot connect to X server"
**Solution**: Run from Pi desktop, not SSH, or use X forwarding:
```bash
ssh -X andrc1@192.168.0.200
export DISPLAY=:0
```

### Issue: "Connection refused" when sending commands
**Solution**: Restart slave services
```bash
ssh andrc1@192.168.0.20X "sudo systemctl restart still_capture.service"
```

### Issue: Cameras not detected (heartbeat fails)
**Possible causes**:
1. Network issue - check ping
2. Wrong subnet - verify 192.168.0.x
3. Service not running on slaves

### Issue: Video stream not displaying
**Solution**: Check video_stream.service on slave
```bash
ssh andrc1@192.168.0.201 "journalctl -u video_stream.service --no-pager | tail -20"
```

---

## Return Protocol

After testing, bring back to MacBook:

1. **Qt log file**: `/home/andrc1/Desktop/qt_test_*.log`
2. **System updatelog**: `/home/andrc1/Desktop/updatelog.txt`
3. **Any error screenshots**

Analyze logs using Claude GERTIE session (Phase 6 of GERTIE protocol).

---

## Next Steps After Successful Testing

1. Document any bugs found
2. Create GitHub issue for each bug
3. Fix critical bugs immediately
4. Proceed to Phase 4 (Video Stream Integration)
5. Update QT_CONVERSION_LOG.txt with results

---

## Quick Reference Commands

```bash
# Start Qt (from Pi)
cd /home/andrc1/camera_system_qt_conversion/src && python3 gertie_qt.py

# Check slave status
ssh andrc1@192.168.0.201 "systemctl status video_stream.service"

# Restart slave services
ssh andrc1@192.168.0.201 "sudo systemctl restart video_stream.service still_capture.service"

# View slave logs
ssh andrc1@192.168.0.201 "journalctl -u video_stream.service -n 50"

# Ping all slaves
for ip in 201 202 203 204 205 206 207; do ping -c 1 192.168.0.$ip; done
```
