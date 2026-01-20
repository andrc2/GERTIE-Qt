#!/bin/bash
# GERTIE - Complete Hybrid Reinstall Script
# Reinstalls working Tkinter services on rep1-7
# NO set -e - continues even if individual slaves fail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"
TKINTER_DIR="/home/andrc1/camera_system_integrated_final"
QT_DIR="/home/andrc1/camera_system_qt_conversion"

SUCCESS=0
FAILED=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a "$LOG_FILE"
}

# Reinstall on one slave - all errors caught with || true
reinstall_slave() {
    local ip=$1
    local name="rep$((ip - 200))"
    
    echo ""
    echo -e "${CYAN}━━━ $name (192.168.0.$ip) ━━━${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "192.168.0.$ip" > /dev/null 2>&1; then
        echo -e "  ${RED}✗ Not reachable${NC}"
        log "[ERROR] $name: Not reachable"
        FAILED=$((FAILED + 1))
        return 0
    fi
    echo -e "  ${GREEN}✓ Reachable${NC}"
    
    # Check Tkinter code exists
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_USER@192.168.0.$ip" "test -f $TKINTER_DIR/slave/video_stream.py" 2>/dev/null; then
        echo -e "  ${RED}✗ Tkinter code missing at $TKINTER_DIR${NC}"
        log "[ERROR] $name: Tkinter codebase missing"
        FAILED=$((FAILED + 1))
        return 0
    fi
    echo -e "  ${GREEN}✓ Tkinter code present${NC}"
    
    # Stop all services
    echo -e "  Stopping services..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl stop gertie-video.service gertie-capture.service video_stream.service still_capture.service 2>/dev/null || true" 2>/dev/null || true
    
    # Disable Qt services
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl disable gertie-video.service gertie-capture.service 2>/dev/null || true" 2>/dev/null || true
    
    # Install video_stream.service
    echo -e "  Installing video_stream.service..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "cat > /tmp/video_stream.service << 'SERVICEEOF'
[Unit]
Description=Video Stream Service (Tkinter)
After=network.target

[Service]
Type=simple
User=andrc1
Group=andrc1
WorkingDirectory=/home/andrc1/camera_system_integrated_final
ExecStart=/usr/bin/python3 /home/andrc1/camera_system_integrated_final/slave/video_stream.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=/home/andrc1/camera_system_integrated_final

[Install]
WantedBy=multi-user.target
SERVICEEOF
sudo cp /tmp/video_stream.service /etc/systemd/system/" 2>/dev/null || true
    
    # Install still_capture.service
    echo -e "  Installing still_capture.service..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "cat > /tmp/still_capture.service << 'SERVICEEOF'
[Unit]
Description=Still Capture Service (Tkinter)
After=network.target video_stream.service
Requires=video_stream.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=andrc1
Group=andrc1
WorkingDirectory=/home/andrc1/camera_system_integrated_final
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/python3 /home/andrc1/camera_system_integrated_final/slave/still_capture.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=/home/andrc1/camera_system_integrated_final

[Install]
WantedBy=multi-user.target
SERVICEEOF
sudo cp /tmp/still_capture.service /etc/systemd/system/" 2>/dev/null || true
    
    # Reload and enable
    echo -e "  Enabling services..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl daemon-reload && sudo systemctl enable video_stream.service still_capture.service" 2>/dev/null || true
    
    # Start services
    echo -e "  Starting video_stream..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl start video_stream.service" 2>/dev/null || true
    sleep 3
    
    echo -e "  Starting still_capture..."
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl start still_capture.service" 2>/dev/null || true
    sleep 2
    
    # Verify
    local video=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "failed")
    local capture=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "failed")
    
    if [ "$video" = "active" ] && [ "$capture" = "active" ]; then
        echo -e "  ${GREEN}✓ READY: video=$video capture=$capture${NC}"
        log "[OK] $name: Tkinter services running"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "  ${RED}✗ FAILED: video=$video capture=$capture${NC}"
        log "[ERROR] $name: Services failed (video=$video capture=$capture)"
        FAILED=$((FAILED + 1))
    fi
    
    return 0
}

# Setup local camera (rep8)
setup_local() {
    echo ""
    echo -e "${CYAN}━━━ rep8 (local) ━━━${NC}"
    
    if [ ! -f "$QT_DIR/local_camera_slave.py" ]; then
        echo -e "  ${RED}✗ local_camera_slave.py missing${NC}"
        FAILED=$((FAILED + 1))
        return 0
    fi
    echo -e "  ${GREEN}✓ Qt code present${NC}"
    
    # Install service if file exists
    if [ -f "$QT_DIR/local_camera_slave.service" ]; then
        sudo cp "$QT_DIR/local_camera_slave.service" /etc/systemd/system/ 2>/dev/null || true
        sudo systemctl daemon-reload 2>/dev/null || true
    fi
    
    # Enable and start
    sudo systemctl enable local_camera_slave.service 2>/dev/null || true
    sudo systemctl restart local_camera_slave.service 2>/dev/null || true
    sleep 2
    
    local status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "failed")
    if [ "$status" = "active" ]; then
        echo -e "  ${GREEN}✓ READY: local=$status${NC}"
        log "[OK] rep8: Qt local camera running"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "  ${RED}✗ FAILED: local=$status${NC}"
        log "[ERROR] rep8: Service failed"
        FAILED=$((FAILED + 1))
    fi
    
    return 0
}

# Status only
status_check() {
    echo "Camera Status:"
    for ip in 201 202 203 204 205 206 207; do
        name="rep$((ip - 200))"
        v=$(ssh -o ConnectTimeout=2 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "?")
        c=$(ssh -o ConnectTimeout=2 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "?")
        if [ "$v" = "active" ] && [ "$c" = "active" ]; then
            echo -e "  ${GREEN}$name: video=$v capture=$c ✓${NC}"
        else
            echo -e "  ${RED}$name: video=$v capture=$c ✗${NC}"
        fi
    done
    l=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "?")
    if [ "$l" = "active" ]; then
        echo -e "  ${GREEN}rep8: local=$l ✓${NC}"
    else
        echo -e "  ${RED}rep8: local=$l ✗${NC}"
    fi
}

# Main
main() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  GERTIE HYBRID REINSTALL                               ║${NC}"
    echo -e "${CYAN}║  rep1-7: Tkinter services                              ║${NC}"
    echo -e "${CYAN}║  rep8:   Qt local camera                               ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    
    log "[REINSTALL] Starting hybrid reinstall"
    
    # Process ALL slaves - no early exit
    reinstall_slave 201
    reinstall_slave 202
    reinstall_slave 203
    reinstall_slave 204
    reinstall_slave 205
    reinstall_slave 206
    reinstall_slave 207
    
    # Local camera
    setup_local
    
    # Summary
    echo ""
    echo -e "${CYAN}━━━ SUMMARY ━━━${NC}"
    echo -e "  ${GREEN}Success: $SUCCESS${NC}"
    echo -e "  ${RED}Failed:  $FAILED${NC}"
    
    log "[REINSTALL] Complete: $SUCCESS success, $FAILED failed"
    
    if [ $FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ ALL 8 CAMERAS READY${NC}"
        echo -e "Run: ${CYAN}./run_qt_with_logging.sh${NC}"
    else
        echo ""
        echo -e "${YELLOW}⚠ $FAILED cameras need attention${NC}"
    fi
}

# Handle arguments
case "$1" in
    --status|-s)
        status_check
        ;;
    --verify|-v)
        echo "Verifying Tkinter code on slaves..."
        for ip in 201 202 203 204 205 206 207; do
            name="rep$((ip - 200))"
            if ssh -o ConnectTimeout=3 "$REMOTE_USER@192.168.0.$ip" "test -f $TKINTER_DIR/slave/video_stream.py" 2>/dev/null; then
                echo -e "  ${GREEN}$name: Tkinter code present ✓${NC}"
            else
                echo -e "  ${RED}$name: Tkinter code MISSING ✗${NC}"
            fi
        done
        ;;
    *)
        main
        ;;
esac
