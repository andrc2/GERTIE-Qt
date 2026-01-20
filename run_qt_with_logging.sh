#!/bin/bash
# GERTIE Qt - GUI Testing Logger
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
# (control1 has RTC battery backup)
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

# Capture system state
log_both "[$TIMESTAMP] [INFO] System state before Qt GUI launch:"

# Check slave services (BOTH gertie-video AND gertie-capture for Qt)
log_both "[$TIMESTAMP] [INFO] Checking slave services..."
for ip in 201 202 203 204 205 206 207; do
    video_status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active gertie-video.service" 2>/dev/null || echo "unreachable")
    capture_status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active gertie-capture.service" 2>/dev/null || echo "unreachable")
    log_both "[$TIMESTAMP] [INFO] rep$((ip - 200)) (192.168.0.$ip): video=$video_status capture=$capture_status"
done

# Local rep8 (local_camera_slave.service handles BOTH video+capture on control1)
status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "not running")
log_both "[$TIMESTAMP] [INFO] rep8 (local): $status (combined video+capture)"

# Network ports
log_both "[$TIMESTAMP] [INFO] Network ports:"
netstat -an 2>/dev/null | grep -E "(5001|5002|6000|6010)" >> "$LATEST_LOG" 2>&1
netstat -an 2>/dev/null | grep -E "(5001|5002|6000|6010)" >> "$CUMULATIVE_LOG" 2>&1

log_both ""
log_both "[$TIMESTAMP] [INFO] Launching Qt GUI..."
log_both ""

# Run Qt GUI with output captured to both logs
cd /home/andrc1/camera_system_qt_conversion/src
python3 gertie_qt.py 2>&1 | tee -a "$LATEST_LOG" | tee -a "$CUMULATIVE_LOG"

# Session end
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
log_both ""
log_both "========================================================================"
log_both "[$TIMESTAMP] SESSION COMPLETE"
log_both "========================================================================"

# ============================================
# POST-SESSION: Collect slave logs for troubleshooting
# ============================================
log_both ""
log_both "[$TIMESTAMP] [INFO] Collecting slave service logs for troubleshooting..."

# Collect resolution and capture logs from each slave
for ip in 201 202 203 204 205 206 207; do
    SLAVE_NAME="rep$((ip - 200))"
    log_both ""
    log_both "--- $SLAVE_NAME (192.168.0.$ip) recent logs ---"
    # Get last 30 lines from both services, filter for key events
    ssh -o ConnectTimeout=3 andrc1@192.168.0.$ip "journalctl -u gertie-video.service -u gertie-capture.service -n 30 --no-pager 2>/dev/null | grep -E 'RESOLUTION|CAPTURE|ERROR|WARNING|Starting|Restarting'" 2>/dev/null | tee -a "$LATEST_LOG" | tee -a "$CUMULATIVE_LOG"
done

# Local rep8 logs
log_both ""
log_both "--- rep8 (local) recent logs ---"
journalctl -u local_camera_slave.service -n 30 --no-pager 2>/dev/null | grep -E 'RESOLUTION|CAPTURE|ERROR|WARNING|Starting|Restarting' | tee -a "$LATEST_LOG" | tee -a "$CUMULATIVE_LOG"

log_both ""
log_both "[$TIMESTAMP] [INFO] Slave log collection complete"
log_both "========================================================================"

# Copy latest to archive
cp "$LATEST_LOG" "$ARCHIVE_LOG"

# ============================================
# AUTOMATED LOG ANALYSIS - Troubleshooting Summary
# ============================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    SESSION ANALYSIS REPORT                         ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Count key events from this session's log
ERRORS=$(grep -c "ERROR" "$LATEST_LOG" 2>/dev/null || echo "0")
WARNINGS=$(grep -c "WARNING\|WARN" "$LATEST_LOG" 2>/dev/null || echo "0")
CAPTURES=$(grep -c "CAPTURE" "$LATEST_LOG" 2>/dev/null || echo "0")
RESOLUTION_CHANGES=$(grep -c "RESOLUTION" "$LATEST_LOG" 2>/dev/null || echo "0")
EXCLUSIVE_EVENTS=$(grep -c "EXCLUSIVE\|exclusive" "$LATEST_LOG" 2>/dev/null || echo "0")
DECODE_LOGS=$(grep -c "DECODE" "$LATEST_LOG" 2>/dev/null || echo "0")

echo "📊 Event Summary:"
echo "   Errors:              $ERRORS"
echo "   Warnings:            $WARNINGS"
echo "   Captures logged:     $CAPTURES"
echo "   Resolution changes:  $RESOLUTION_CHANGES"
echo "   Exclusive mode:      $EXCLUSIVE_EVENTS"
echo "   Decode logs:         $DECODE_LOGS"
echo ""

# Show errors if any
if [ "$ERRORS" -gt 0 ]; then
    echo "❌ ERRORS FOUND:"
    echo "────────────────────────────────────────"
    grep "ERROR" "$LATEST_LOG" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show warnings if any
if [ "$WARNINGS" -gt 0 ]; then
    echo "⚠️  WARNINGS:"
    echo "────────────────────────────────────────"
    grep -E "WARNING|WARN" "$LATEST_LOG" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show resolution events
if [ "$RESOLUTION_CHANGES" -gt 0 ]; then
    echo "📐 RESOLUTION EVENTS:"
    echo "────────────────────────────────────────"
    grep "RESOLUTION" "$LATEST_LOG" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show capture events
if [ "$CAPTURES" -gt 0 ]; then
    echo "📷 CAPTURE EVENTS:"
    echo "────────────────────────────────────────"
    grep "CAPTURE" "$LATEST_LOG" | tail -10
    echo "────────────────────────────────────────"
    echo ""
fi

# Show decode logs (frame dimensions)
if [ "$DECODE_LOGS" -gt 0 ]; then
    echo "🖼️  FRAME DIMENSIONS (from DECODE logs):"
    echo "────────────────────────────────────────"
    grep "DECODE" "$LATEST_LOG" | tail -8
    echo "────────────────────────────────────────"
    echo ""
fi

# Show exclusive mode events
if [ "$EXCLUSIVE_EVENTS" -gt 0 ]; then
    echo "🔳 EXCLUSIVE MODE EVENTS:"
    echo "────────────────────────────────────────"
    grep -iE "EXCLUSIVE|exclusive" "$LATEST_LOG" | tail -8
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
echo "║    grep RESOLUTION $LATEST_LOG"
echo "║    grep CAPTURE $LATEST_LOG"
echo "║    grep DECODE $LATEST_LOG"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
