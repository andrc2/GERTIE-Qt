#!/bin/bash
# GERTIE - Sync Qt Slave Code to RAW-Capable Cameras (rep2, rep8)
# This syncs the Qt version of still_capture.py which has RAW support
# Rep2 = 192.168.0.202 (dorsal), Rep8 = local (lateral)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"
QT_DIR="/home/andrc1/camera_system_qt_conversion"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SYNC_RAW] $@" | tee -a "$LOG_FILE"
}

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  GERTIE - Sync RAW Capture Code to rep2 + rep8  ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

log "Starting RAW code sync to rep2 and rep8"

# ============================================================
# REP2 (192.168.0.202) - Remote slave
# ============================================================
echo -e "${YELLOW}━━━ REP2 (192.168.0.202 - Dorsal) ━━━${NC}"

if ping -c 1 -W 2 192.168.0.202 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Reachable${NC}"
    
    # Sync Qt slave code
    echo -e "  Syncing Qt slave code..."
    scp -o ConnectTimeout=5 "$QT_DIR/slave/still_capture.py" "$REMOTE_USER@192.168.0.202:$QT_DIR/slave/" 2>/dev/null && \
        echo -e "  ${GREEN}✓ still_capture.py synced${NC}" || \
        echo -e "  ${RED}✗ Failed to sync still_capture.py${NC}"
    
    # Sync shared config (has RAW settings)
    scp -o ConnectTimeout=5 -r "$QT_DIR/shared/" "$REMOTE_USER@192.168.0.202:$QT_DIR/" 2>/dev/null && \
        echo -e "  ${GREEN}✓ shared/ synced${NC}" || \
        echo -e "  ${RED}✗ Failed to sync shared/${NC}"
    
    # Check which service is running (Tkinter or Qt)
    ACTIVE_SERVICE=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.202" "systemctl is-active still_capture.service 2>/dev/null || systemctl is-active gertie-capture.service 2>/dev/null || echo 'none'" 2>/dev/null)
    echo -e "  Active capture service: $ACTIVE_SERVICE"
    
    # Update the still_capture.service to use Qt code path
    echo -e "  Updating service to use Qt slave code..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.202" "cat > /tmp/still_capture.service << 'EOF'
[Unit]
Description=Still Capture Service (Qt with RAW support)
After=network.target video_stream.service
Requires=video_stream.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=andrc1
Group=andrc1
WorkingDirectory=/home/andrc1/camera_system_qt_conversion
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/python3 /home/andrc1/camera_system_qt_conversion/slave/still_capture.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=/home/andrc1/camera_system_qt_conversion
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF
sudo cp /tmp/still_capture.service /etc/systemd/system/still_capture.service
sudo systemctl daemon-reload
sudo systemctl restart still_capture.service" 2>/dev/null && \
        echo -e "  ${GREEN}✓ Service updated and restarted${NC}" || \
        echo -e "  ${RED}✗ Failed to update service${NC}"
    
    # Verify
    sleep 2
    STATUS=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.202" "systemctl is-active still_capture.service" 2>/dev/null || echo "failed")
    if [ "$STATUS" = "active" ]; then
        echo -e "  ${GREEN}✓ REP2 ready for RAW capture${NC}"
        log "[OK] rep2: Qt slave code deployed, service active"
    else
        echo -e "  ${RED}✗ Service not active: $STATUS${NC}"
        log "[ERROR] rep2: Service not active after update"
    fi
else
    echo -e "  ${RED}✗ Not reachable${NC}"
    log "[ERROR] rep2: Not reachable"
fi

# ============================================================
# REP8 (127.0.0.1) - Local slave on control1
# ============================================================
echo ""
echo -e "${YELLOW}━━━ REP8 (local - Lateral) ━━━${NC}"

# Rep8 is local, so just verify the code is in place
if [ -f "$QT_DIR/slave/still_capture.py" ]; then
    echo -e "  ${GREEN}✓ Qt slave code present${NC}"
else
    echo -e "  ${RED}✗ Qt slave code missing at $QT_DIR/slave/still_capture.py${NC}"
    log "[ERROR] rep8: Qt slave code missing"
fi

# Check local_camera_slave.service or combined service
LOCAL_STATUS=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
echo -e "  Local camera service: $LOCAL_STATUS"

if [ "$LOCAL_STATUS" = "active" ]; then
    echo -e "  Restarting local camera service to pick up changes..."
    sudo systemctl restart local_camera_slave.service
    sleep 2
    LOCAL_STATUS=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "failed")
    if [ "$LOCAL_STATUS" = "active" ]; then
        echo -e "  ${GREEN}✓ REP8 ready for RAW capture${NC}"
        log "[OK] rep8: Service restarted with Qt code"
    else
        echo -e "  ${RED}✗ Service restart failed${NC}"
        log "[ERROR] rep8: Service restart failed"
    fi
else
    echo -e "  ${YELLOW}⚠ No local_camera_slave.service - will use Qt code when GUI launches${NC}"
    log "[WARN] rep8: No service, will use embedded local camera"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RAW Code Sync Complete!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "To test RAW capture:"
echo "  1. Run ./run_qt_with_logging.sh"
echo "  2. Press 'S' for settings, select REP2 or REP8"
echo "  3. Enable 'RAW Capture' checkbox"
echo "  4. Click Apply, then capture"
echo "  5. Check hires_captures/ for .jpg AND .dng files"
echo ""

log "RAW code sync completed"
