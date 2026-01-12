#!/bin/bash
# GERTIE Qt - GUI Testing Logger
# Creates updatelog.txt with system state and GUI output

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Start logging session
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] GERTIE Qt TEST SESSION STARTED" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Capture system state
echo "[$TIMESTAMP] [INFO] System state before Qt GUI launch:" >> "$LOG_FILE"

# Check slave services
echo "[$TIMESTAMP] [INFO] Checking slave services..." >> "$LOG_FILE"
for ip in 201 202 203 204 205 206 207; do
    status=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active video_stream.service" 2>/dev/null || echo "unreachable")
    echo "[$TIMESTAMP] [INFO] rep$((ip - 200)) (192.168.0.$ip): $status" >> "$LOG_FILE"
done

# Local rep8
status=$(systemctl is-active video_stream.service 2>/dev/null || echo "not running")
echo "[$TIMESTAMP] [INFO] rep8 (local): $status" >> "$LOG_FILE"

# Network ports
echo "[$TIMESTAMP] [INFO] Network ports:" >> "$LOG_FILE"
netstat -an 2>/dev/null | grep -E "(5001|5002|6000|6010)" >> "$LOG_FILE" 2>&1 || ss -an | grep -E "(5001|5002|6000|6010)" >> "$LOG_FILE" 2>&1

echo "" >> "$LOG_FILE"
echo "[$TIMESTAMP] [INFO] Launching Qt GUI..." >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Run Qt GUI with output captured
cd /home/andrc1/camera_system_qt_conversion/src
python3 gertie_qt.py 2>&1 | tee -a "$LOG_FILE"

# Session end
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] GERTIE Qt TEST SESSION ENDED" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
