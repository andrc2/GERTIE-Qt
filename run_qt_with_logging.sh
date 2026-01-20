#!/bin/bash
# GERTIE Qt - GUI Testing Logger with Comprehensive Slave Logging
# Creates:
#   - updatelog.txt (cumulative history)
#   - qt_latest.log (just this session - overwrites each time)
#   - qt_YYYYMMDD_HHMMSS.log (timestamped archive)

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TIMESTAMP_FILE=$(date '+%Y%m%d_%H%M%S')

# Log locations
LOG_DIR="/home/andrc1/Desktop"
CUMULATIVE_LOG="$LOG_DIR/updatelog.txt"
LATEST_LOG="$LOG_DIR/qt_latest.log"
ARCHIVE_LOG="$LOG_DIR/qt_${TIMESTAMP_FILE}.log"

# Start fresh latest log
echo "========================================" > "$LATEST_LOG"
echo "[$TIMESTAMP] GERTIE Qt TEST SESSION" >> "$LATEST_LOG"
echo "========================================" >> "$LATEST_LOG"

# Also append to cumulative
echo "" >> "$CUMULATIVE_LOG"
echo "========================================" >> "$CUMULATIVE_LOG"
echo "[$TIMESTAMP] GERTIE Qt TEST SESSION STARTED" >> "$CUMULATIVE_LOG"
echo "========================================" >> "$CUMULATIVE_LOG"

# Function to log to both files
log_both() {
    echo "$1" >> "$LATEST_LOG"
    echo "$1" >> "$CUMULATIVE_LOG"
}

# ============================================
# TIME SYNC: Sync all Pi clocks to control1
# ============================================
log_both "[$TIMESTAMP] [INFO] Syncing time to all cameras from control1 RTC..."
echo "Syncing time to all cameras..."

CONTROL1_TIME=$(date '+%Y-%m-%d %H:%M:%S')
log_both "[$TIMESTAMP] [INFO] Control1 time: $CONTROL1_TIME"

SYNC_SUCCESS=0
SYNC_FAIL=0

for ip in 201 202 203 204 205 206 207; do
    SLAVE_NAME="rep$((ip - 200))"
    if ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "sudo date -s '$CONTROL1_TIME'" > /dev/null 2>&1; then
        log_both "[$TIMESTAMP] [INFO] $SLAVE_NAME (192.168.0.$ip): Time synced ✓"
        ((SYNC_SUCCESS++))
    else
        log_both "[$TIMESTAMP] [WARN] $SLAVE_NAME (192.168.0.$ip): Time sync FAILED"
        ((SYNC_FAIL++))
    fi
done

log_both "[$TIMESTAMP] [INFO] Time sync complete: $SYNC_SUCCESS success, $SYNC_FAIL failed"
echo "Time sync complete: $SYNC_SUCCESS/7 cameras synced"
log_both ""

# ============================================
# PRE-SESSION: Capture system state
# ============================================
log_both "[$TIMESTAMP] [INFO] System state before Qt GUI launch:"

# Check slave services (Tkinter: video_stream + still_capture)
log_both "[$TIMESTAMP] [INFO] Checking slave services..."
for ip in 201 202 203 204 205 206 207; do
    video_status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active video_stream.service" 2>/dev/null || echo "unreachable")
    capture_status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active still_capture.service" 2>/dev/null || echo "unreachable")
    log_both "[$TIMESTAMP] [INFO] rep$((ip - 200)) (192.168.0.$ip): video=$video_status capture=$capture_status"
done

# Local rep8 (local_camera_slave.service handles BOTH video+capture on control1)
status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "not running")
log_both "[$TIMESTAMP] [INFO] rep8 (local): $status (combined video+capture)"

# Network ports
log_both "[$TIMESTAMP] [INFO] Network ports:"
netstat -an 2>/dev/null | grep -E "(5001|5002|5003|5004|6000|6010)" >> "$LATEST_LOG" 2>&1
netstat -an 2>/dev/null | grep -E "(5001|5002|5003|5004|6000|6010)" >> "$CUMULATIVE_LOG" 2>&1

log_both ""
log_both "[$TIMESTAMP] [INFO] Launching Qt GUI..."
log_both ""

# ============================================
# RUN GUI - Capture all output
# ============================================
cd /home/andrc1/camera_system_qt_conversion/src
python3 gertie_qt.py 2>&1 | tee -a "$LATEST_LOG" | tee -a "$CUMULATIVE_LOG"

# ============================================
# POST-SESSION: Comprehensive slave log collection
# ============================================
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
log_both ""
log_both "========================================================================"
log_both "[$TIMESTAMP] SESSION COMPLETE"
log_both "========================================================================"

log_both ""
log_both "[$TIMESTAMP] [INFO] Collecting COMPREHENSIVE slave logs..."
log_both ""

# Define log collection patterns for comprehensive capture
# These patterns capture all relevant slave activity
SLAVE_PATTERNS='CAPTURE|RESOLUTION|ERROR|WARNING|SETTINGS|brightness|contrast|iso|TRANSFORM|flip|rotate|crop|grayscale|START_STREAM|STOP_STREAM|RESTART|TCP|UDP|socket|bind|connect|send|recv|Camera|picamera|frame|JPEG|quality|Starting|Stopping|Restarting|Exception|Traceback|Failed|Success|timeout|port|import|module|shared|config'

for ip in 201 202 203 204 205 206 207; do
    SLAVE_NAME="rep$((ip - 200))"
    log_both ""
    log_both "┌─────────────────────────────────────────────────────────────────────┐"
    log_both "│ $SLAVE_NAME (192.168.0.$ip) - COMPREHENSIVE SLAVE LOGS              │"
    log_both "└─────────────────────────────────────────────────────────────────────┘"
    
    # Video stream service logs (full session)
    log_both ""
    log_both "[SLAVE_VIDEO:$SLAVE_NAME] === video_stream.service logs ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE '$SLAVE_PATTERNS' | tail -50" 2>/dev/null | while read line; do
        log_both "[SLAVE_VIDEO:$SLAVE_NAME] $line"
    done
    
    # Still capture service logs (full session)  
    log_both ""
    log_both "[SLAVE_CAPTURE:$SLAVE_NAME] === still_capture.service logs ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE '$SLAVE_PATTERNS' | tail -50" 2>/dev/null | while read line; do
        log_both "[SLAVE_CAPTURE:$SLAVE_NAME] $line"
    done
    
    # Service status
    log_both ""
    log_both "[SLAVE_STATUS:$SLAVE_NAME] === Service Status ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "systemctl status video_stream.service still_capture.service --no-pager 2>/dev/null | head -20" 2>/dev/null | while read line; do
        log_both "[SLAVE_STATUS:$SLAVE_NAME] $line"
    done
    
    # Check for any crashes or restarts
    log_both ""
    log_both "[SLAVE_HEALTH:$SLAVE_NAME] === Recent restarts/crashes ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'Started|Stopped|Main process exited|Failed|systemd' | tail -10" 2>/dev/null | while read line; do
        log_both "[SLAVE_HEALTH:$SLAVE_NAME] $line"
    done
    
    # Python errors/exceptions
    log_both ""
    log_both "[SLAVE_ERROR:$SLAVE_NAME] === Python errors ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'Error|Exception|Traceback|ImportError|ModuleNotFound|AttributeError|TypeError|ValueError|KeyError|IndexError|OSError|IOError|RuntimeError' | tail -20" 2>/dev/null | while read line; do
        log_both "[SLAVE_ERROR:$SLAVE_NAME] $line"
    done
    
    # Resolution changes
    log_both ""
    log_both "[SLAVE_RESOLUTION:$SLAVE_NAME] === Resolution events ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'resolution|RESOLUTION|[0-9]+x[0-9]+|4056|3040|1280|960|640|480' | tail -15" 2>/dev/null | while read line; do
        log_both "[SLAVE_RESOLUTION:$SLAVE_NAME] $line"
    done
    
    # Capture events
    log_both ""
    log_both "[SLAVE_CAPTURE_EVENT:$SLAVE_NAME] === Capture events ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'CAPTURE|capture|still|image|JPEG|save|send|TCP|connect' | tail -20" 2>/dev/null | while read line; do
        log_both "[SLAVE_CAPTURE_EVENT:$SLAVE_NAME] $line"
    done
    
    # Network/socket events
    log_both ""
    log_both "[SLAVE_NETWORK:$SLAVE_NAME] === Network events ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'socket|bind|connect|send|recv|port|UDP|TCP|5001|5002|5003|5004|6000' | tail -15" 2>/dev/null | while read line; do
        log_both "[SLAVE_NETWORK:$SLAVE_NAME] $line"
    done
    
    # Settings changes
    log_both ""
    log_both "[SLAVE_SETTINGS:$SLAVE_NAME] === Settings events ==="
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u video_stream.service -u still_capture.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'SETTINGS|settings|brightness|contrast|iso|saturation|quality|SET_' | tail -15" 2>/dev/null | while read line; do
        log_both "[SLAVE_SETTINGS:$SLAVE_NAME] $line"
    done
done

# Local rep8 logs
log_both ""
log_both "┌─────────────────────────────────────────────────────────────────────┐"
log_both "│ rep8 (local/127.0.0.1) - LOCAL CAMERA LOGS                         │"
log_both "└─────────────────────────────────────────────────────────────────────┘"

log_both ""
log_both "[SLAVE_LOCAL:rep8] === local_camera_slave.service logs ==="
journalctl -u local_camera_slave.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE "$SLAVE_PATTERNS" | tail -50 | while read line; do
    log_both "[SLAVE_LOCAL:rep8] $line"
done

log_both ""
log_both "[SLAVE_LOCAL_ERROR:rep8] === Python errors ==="
journalctl -u local_camera_slave.service --since '1 hour ago' --no-pager 2>/dev/null | grep -iE 'Error|Exception|Traceback|Failed' | tail -20 | while read line; do
    log_both "[SLAVE_LOCAL_ERROR:rep8] $line"
done

log_both ""
log_both "[$TIMESTAMP] [INFO] Slave log collection complete"
log_both "========================================================================"

# Copy latest to archive
cp "$LATEST_LOG" "$ARCHIVE_LOG"

# ============================================
# AUTOMATED LOG ANALYSIS
# ============================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    SESSION ANALYSIS REPORT                         ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Count key events from this session's log
ERRORS=$(grep -c "ERROR" "$LATEST_LOG" 2>/dev/null || echo "0")
WARNINGS=$(grep -c "WARNING\|WARN" "$LATEST_LOG" 2>/dev/null || echo "0")
CAPTURES=$(grep -c "\[CAPTURE\]" "$LATEST_LOG" 2>/dev/null || echo "0")
RESOLUTION_CHANGES=$(grep -c "\[RESOLUTION\]" "$LATEST_LOG" 2>/dev/null || echo "0")
EXCLUSIVE_EVENTS=$(grep -c "EXCLUSIVE\|exclusive" "$LATEST_LOG" 2>/dev/null || echo "0")
DECODE_LOGS=$(grep -c "\[DECODE\]" "$LATEST_LOG" 2>/dev/null || echo "0")
SLAVE_ERRORS=$(grep -c "SLAVE_ERROR" "$LATEST_LOG" 2>/dev/null || echo "0")
SLAVE_CAPTURES=$(grep -c "SLAVE_CAPTURE" "$LATEST_LOG" 2>/dev/null || echo "0")

echo "📊 Event Summary:"
echo "   GUI Errors:          $ERRORS"
echo "   GUI Warnings:        $WARNINGS"
echo "   Captures logged:     $CAPTURES"
echo "   Resolution changes:  $RESOLUTION_CHANGES"
echo "   Exclusive mode:      $EXCLUSIVE_EVENTS"
echo "   Decode logs:         $DECODE_LOGS"
echo "   Slave errors:        $SLAVE_ERRORS"
echo "   Slave capture logs:  $SLAVE_CAPTURES"
echo ""

# Show errors if any
if [ "$ERRORS" -gt 0 ]; then
    echo "❌ GUI ERRORS FOUND:"
    echo "────────────────────────────────────────"
    grep "ERROR" "$LATEST_LOG" | grep -v "SLAVE_ERROR" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show slave errors if any
if [ "$SLAVE_ERRORS" -gt 0 ]; then
    echo "❌ SLAVE ERRORS FOUND:"
    echo "────────────────────────────────────────"
    grep "SLAVE_ERROR" "$LATEST_LOG" | tail -15
    echo "────────────────────────────────────────"
    echo ""
fi

# Show capture events
if [ "$CAPTURES" -gt 0 ]; then
    echo "📷 CAPTURE EVENTS:"
    echo "────────────────────────────────────────"
    grep "\[CAPTURE\]" "$LATEST_LOG" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show decode logs (frame dimensions)
if [ "$DECODE_LOGS" -gt 0 ]; then
    echo "🖼️  FRAME DIMENSIONS (from DECODE logs):"
    echo "────────────────────────────────────────"
    grep "\[DECODE\]" "$LATEST_LOG" | tail -8
    echo "────────────────────────────────────────"
    echo ""
fi

# FPS summary
FPS_LINE=$(grep "FPS:" "$LATEST_LOG" | tail -1)
if [ -n "$FPS_LINE" ]; then
    echo "📈 Final Stats: $FPS_LINE"
    echo ""
fi

# Session summary line
SESSION_LINE=$(grep "Frames:" "$LATEST_LOG" | tail -1)
if [ -n "$SESSION_LINE" ]; then
    echo "📊 Session: $SESSION_LINE"
    echo ""
fi

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                         LOG FILES                                  ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║  Latest:     $LATEST_LOG"
echo "║  Archive:    $ARCHIVE_LOG"
echo "║  Cumulative: $CUMULATIVE_LOG"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║  Quick commands:                                                   ║"
echo "║    grep ERROR $LATEST_LOG"
echo "║    grep SLAVE_ERROR $LATEST_LOG"
echo "║    grep SLAVE_CAPTURE $LATEST_LOG"
echo "║    grep '\[CAPTURE\]' $LATEST_LOG"
echo "║    grep '\[DECODE\]' $LATEST_LOG"
echo "║    grep '\[RESOLUTION\]' $LATEST_LOG"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
