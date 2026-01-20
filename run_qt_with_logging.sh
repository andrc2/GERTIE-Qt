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

# Check slave services (gertie-slave.service for Qt)
log_both "[$TIMESTAMP] [INFO] Checking slave services..."
for ip in 201 202 203 204 205 206 207; do
    status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active gertie-slave.service" 2>/dev/null || echo "unreachable")
    log_both "[$TIMESTAMP] [INFO] rep$((ip - 200)) (192.168.0.$ip): $status"
done

# Local rep8 (local_camera_slave.service on control1)
status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "not running")
log_both "[$TIMESTAMP] [INFO] rep8 (local): $status"

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

# Copy latest to archive
cp "$LATEST_LOG" "$ARCHIVE_LOG"

echo ""
echo "Logs saved to:"
echo "  Latest:     $LATEST_LOG"
echo "  Archive:    $ARCHIVE_LOG"
echo "  Cumulative: $CUMULATIVE_LOG"
