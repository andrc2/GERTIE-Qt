#!/bin/bash
# GERTIE Qt - Deploy Code to All Slaves
# This script ACTUALLY syncs code (unlike sync_to_slaves.sh which only restarts services)

set -e

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"
LOCAL_DIR="/home/andrc1/camera_system_qt_conversion"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a "$LOG_FILE"
}

deploy_to_slave() {
    local ip=$1
    local name="rep$((${ip##*.} - 200))"
    
    echo -e "${CYAN}Deploying to $name ($ip)...${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "$ip" &> /dev/null; then
        echo -e "  ${RED}$name: unreachable ✗${NC}"
        return 1
    fi
    
    # Sync slave code
    echo -e "  ${YELLOW}Syncing slave/ directory...${NC}"
    rsync -av --exclude='__pycache__' --exclude='*.pyc' \
        "$LOCAL_DIR/slave/" "$REMOTE_USER@$ip:$LOCAL_DIR/slave/" 2>/dev/null
    
    # Sync shared code
    echo -e "  ${YELLOW}Syncing shared/ directory...${NC}"
    rsync -av --exclude='__pycache__' --exclude='*.pyc' \
        "$LOCAL_DIR/shared/" "$REMOTE_USER@$ip:$LOCAL_DIR/shared/" 2>/dev/null
    
    # Sync service files
    echo -e "  ${YELLOW}Syncing service files...${NC}"
    rsync -av "$LOCAL_DIR/"*.service "$REMOTE_USER@$ip:$LOCAL_DIR/" 2>/dev/null || true
    
    # Restart services
    echo -e "  ${YELLOW}Restarting services...${NC}"
    ssh "$REMOTE_USER@$ip" "sudo systemctl restart video_stream.service" 2>/dev/null || true
    sleep 2
    ssh "$REMOTE_USER@$ip" "sudo systemctl restart still_capture.service" 2>/dev/null || true
    sleep 1
    
    # Verify services are running
    local video=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "inactive")
    local capture=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "inactive")
    
    if [ "$video" = "active" ] && [ "$capture" = "active" ]; then
        echo -e "  ${GREEN}$name: deployed and running ✓${NC}"
        log "[DEPLOY] $name: Code synced and services restarted"
        return 0
    else
        echo -e "  ${RED}$name: services not running (video=$video capture=$capture) ✗${NC}"
        log "[DEPLOY] $name: Deploy failed (video=$video capture=$capture)"
        return 1
    fi
}

# Main
main() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  GERTIE Qt: Deploy Code to All Slaves      ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    
    log "[DEPLOY] Starting code deployment to all slaves"
    
    local ok=0
    local fail=0
    
    # Deploy to all remote slaves (rep1-7)
    echo -e "${CYAN}Deploying to Remote Slaves:${NC}"
    for ip in 192.168.0.201 192.168.0.202 192.168.0.203 192.168.0.204 192.168.0.205 192.168.0.206 192.168.0.207; do
        if deploy_to_slave "$ip"; then
            ((ok++))
        else
            ((fail++))
        fi
        echo ""
    done
    
    # Summary
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Deployed: $ok${NC}  ${RED}Failed: $fail${NC}"
    echo -e "${CYAN}════════════════════════════════════════════${NC}"
    
    log "[DEPLOY] Complete: $ok deployed, $fail failed"
    
    if [ $fail -gt 0 ]; then
        echo -e "${YELLOW}Some deployments failed. Check connectivity and try again.${NC}"
        return 1
    fi
    
    echo -e "${GREEN}All slaves updated! Restart the Qt GUI to test.${NC}"
    return 0
}

main "$@"
