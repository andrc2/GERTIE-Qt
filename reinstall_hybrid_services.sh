#!/bin/bash
# GERTIE - Complete Hybrid Reinstall Script
# Reinstalls working Tkinter services on rep1-7 while preserving Qt GUI on control1
# 
# Architecture:
#   rep1-7: Tkinter slave code (camera_system_integrated_final) - PROVEN WORKING
#   rep8:   Qt local camera (camera_system_qt_conversion) - WORKING
#   GUI:    Qt GUI on control1 - ALL IMPROVEMENTS PRESERVED

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"

# Paths
TKINTER_DIR="/home/andrc1/camera_system_integrated_final"
QT_DIR="/home/andrc1/camera_system_qt_conversion"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $@"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    log "$1"
    echo "========================================" | tee -a "$LOG_FILE"
}

# Service file contents (embedded to ensure consistency)
VIDEO_STREAM_SERVICE='[Unit]
Description=Video Stream Service (Tkinter - Working)
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
WantedBy=multi-user.target'

STILL_CAPTURE_SERVICE='[Unit]
Description=Still Capture Service (Tkinter - Working)
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
WantedBy=multi-user.target'

# Reinstall services on a remote slave
reinstall_remote_slave() {
    local ip=$1
    local name="rep$((${ip##*.} - 200))"
    
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$name (192.168.0.$ip)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "192.168.0.$ip" &> /dev/null; then
        echo -e "${RED}✗ Not reachable - SKIPPING${NC}"
        log "[ERROR] $name: Not reachable"
        return 1
    fi
    echo -e "${GREEN}✓ Reachable${NC}"
    
    # Step 1: Check if Tkinter codebase exists
    echo -e "\n${YELLOW}[1/6] Checking Tkinter codebase...${NC}"
    if ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "test -f $TKINTER_DIR/slave/video_stream.py" 2>/dev/null; then
        echo -e "${GREEN}✓ Tkinter codebase present${NC}"
    else
        echo -e "${RED}✗ Tkinter codebase MISSING at $TKINTER_DIR${NC}"
        echo -e "${YELLOW}  This slave needs the Tkinter code synced first!${NC}"
        log "[ERROR] $name: Tkinter codebase missing"
        return 1
    fi
    
    # Step 2: Stop any running services (Qt or Tkinter)
    echo -e "\n${YELLOW}[2/6] Stopping all camera services...${NC}"
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl stop gertie-video.service gertie-capture.service video_stream.service still_capture.service 2>/dev/null || true"
    echo -e "${GREEN}✓ Services stopped${NC}"
    
    # Step 3: Disable Qt services if they exist
    echo -e "\n${YELLOW}[3/6] Disabling Qt services...${NC}"
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl disable gertie-video.service gertie-capture.service 2>/dev/null || true"
    echo -e "${GREEN}✓ Qt services disabled${NC}"
    
    # Step 4: Install Tkinter service files
    echo -e "\n${YELLOW}[4/6] Installing Tkinter service files...${NC}"
    
    # Write video_stream.service
    echo "$VIDEO_STREAM_SERVICE" | ssh "$REMOTE_USER@192.168.0.$ip" "sudo tee /etc/systemd/system/video_stream.service > /dev/null"
    echo -e "  ${GREEN}✓ video_stream.service installed${NC}"
    
    # Write still_capture.service
    echo "$STILL_CAPTURE_SERVICE" | ssh "$REMOTE_USER@192.168.0.$ip" "sudo tee /etc/systemd/system/still_capture.service > /dev/null"
    echo -e "  ${GREEN}✓ still_capture.service installed${NC}"
    
    # Reload systemd
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl daemon-reload"
    echo -e "  ${GREEN}✓ systemd daemon reloaded${NC}"
    
    # Step 5: Enable and start services
    echo -e "\n${YELLOW}[5/6] Enabling and starting Tkinter services...${NC}"
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl enable video_stream.service still_capture.service"
    echo -e "  ${GREEN}✓ Services enabled${NC}"
    
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl start video_stream.service"
    sleep 2
    ssh "$REMOTE_USER@192.168.0.$ip" "sudo systemctl start still_capture.service"
    echo -e "  ${GREEN}✓ Services started${NC}"
    
    # Step 6: Verify
    echo -e "\n${YELLOW}[6/6] Verifying services...${NC}"
    local video_status=$(ssh "$REMOTE_USER@192.168.0.$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "failed")
    local capture_status=$(ssh "$REMOTE_USER@192.168.0.$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "failed")
    
    if [ "$video_status" = "active" ] && [ "$capture_status" = "active" ]; then
        echo -e "  ${GREEN}✓ video_stream.service: $video_status${NC}"
        echo -e "  ${GREEN}✓ still_capture.service: $capture_status${NC}"
        echo -e "\n${GREEN}${BOLD}✓ $name READY${NC}"
        log "[OK] $name: Tkinter services installed and running"
        return 0
    else
        echo -e "  ${RED}✗ video_stream.service: $video_status${NC}"
        echo -e "  ${RED}✗ still_capture.service: $capture_status${NC}"
        echo -e "\n${RED}${BOLD}✗ $name FAILED${NC}"
        log "[ERROR] $name: Services not running (video=$video_status capture=$capture_status)"
        return 1
    fi
}

# Setup rep8 (local camera on control1)
setup_local_camera() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}rep8 (local on control1)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check if Qt local_camera_slave.py exists
    echo -e "\n${YELLOW}[1/4] Checking Qt local camera code...${NC}"
    if [ -f "$QT_DIR/local_camera_slave.py" ]; then
        echo -e "${GREEN}✓ local_camera_slave.py present${NC}"
    else
        echo -e "${RED}✗ local_camera_slave.py MISSING${NC}"
        return 1
    fi
    
    # Check service file
    echo -e "\n${YELLOW}[2/4] Checking service file...${NC}"
    if [ -f "/etc/systemd/system/local_camera_slave.service" ]; then
        echo -e "${GREEN}✓ Service file exists${NC}"
    else
        echo -e "${YELLOW}  Installing service file...${NC}"
        sudo cp "$QT_DIR/local_camera_slave.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        echo -e "${GREEN}✓ Service file installed${NC}"
    fi
    
    # Enable and restart
    echo -e "\n${YELLOW}[3/4] Starting local camera service...${NC}"
    sudo systemctl enable local_camera_slave.service 2>/dev/null || true
    sudo systemctl restart local_camera_slave.service
    sleep 2
    
    # Verify
    echo -e "\n${YELLOW}[4/4] Verifying...${NC}"
    local status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "failed")
    if [ "$status" = "active" ]; then
        echo -e "  ${GREEN}✓ local_camera_slave.service: $status${NC}"
        echo -e "\n${GREEN}${BOLD}✓ rep8 READY${NC}"
        log "[OK] rep8: Qt local camera service running"
        return 0
    else
        echo -e "  ${RED}✗ local_camera_slave.service: $status${NC}"
        echo -e "\n${RED}${BOLD}✗ rep8 FAILED${NC}"
        log "[ERROR] rep8: Service not running ($status)"
        return 1
    fi
}

# Main
main() {
    log_section "HYBRID REINSTALL: Tkinter slaves + Qt GUI"
    
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║         GERTIE HYBRID REINSTALL                                  ║"
    echo "║                                                                  ║"
    echo "║  rep1-7: Tkinter slave services (camera_system_integrated_final) ║"
    echo "║  rep8:   Qt local camera (camera_system_qt_conversion)           ║"
    echo "║  GUI:    Qt with all improvements (resolution, keyboard, etc)    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    local success=0
    local failed=0
    
    # Process remote slaves (rep1-7)
    for ip in 201 202 203 204 205 206 207; do
        if reinstall_remote_slave "$ip"; then
            ((success++))
        else
            ((failed++))
        fi
    done
    
    # Process local camera (rep8)
    if setup_local_camera; then
        ((success++))
    else
        ((failed++))
    fi
    
    # Summary
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}SUMMARY${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}Success: $success${NC}"
    echo -e "  ${RED}Failed:  $failed${NC}"
    
    log "[SUMMARY] Reinstall complete: $success success, $failed failed"
    
    if [ $failed -eq 0 ]; then
        echo -e "\n${GREEN}${BOLD}✓ ALL 8 CAMERAS READY${NC}"
        echo -e "\n${YELLOW}Next: Run ./run_qt_with_logging.sh to test${NC}"
        return 0
    else
        echo -e "\n${RED}${BOLD}✗ SOME CAMERAS FAILED - Check logs above${NC}"
        return 1
    fi
}

# Quick status check
if [ "$1" = "--status" ] || [ "$1" = "-s" ]; then
    echo "Checking camera status..."
    echo ""
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
    local_status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "?")
    if [ "$local_status" = "active" ]; then
        echo -e "  ${GREEN}rep8: local=$local_status ✓${NC}"
    else
        echo -e "  ${RED}rep8: local=$local_status ✗${NC}"
    fi
    exit 0
fi

# Verify only (no changes)
if [ "$1" = "--verify" ] || [ "$1" = "-v" ]; then
    echo "Verifying Tkinter codebase on all slaves..."
    echo ""
    for ip in 201 202 203 204 205 206 207; do
        name="rep$((ip - 200))"
        if ssh -o ConnectTimeout=3 "$REMOTE_USER@192.168.0.$ip" "test -f $TKINTER_DIR/slave/video_stream.py && test -f $TKINTER_DIR/slave/still_capture.py" 2>/dev/null; then
            echo -e "  ${GREEN}$name: Tkinter codebase present ✓${NC}"
        else
            echo -e "  ${RED}$name: Tkinter codebase MISSING ✗${NC}"
        fi
    done
    exit 0
fi

main "$@"
