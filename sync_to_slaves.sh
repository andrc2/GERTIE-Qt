#!/bin/bash
# GERTIE Qt - Hybrid Deployment Script
# Qt GUI on control1 + Tkinter slave services on rep1-7
# Logs to /home/andrc1/Desktop/updatelog.txt

set -e

# Configuration
LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"
REMOTE_SLAVES=(
    "192.168.0.201"  # rep1
    "192.168.0.202"  # rep2
    "192.168.0.203"  # rep3
    "192.168.0.204"  # rep4
    "192.168.0.205"  # rep5
    "192.168.0.206"  # rep6
    "192.168.0.207"  # rep7
)
QT_DIR="/home/andrc1/camera_system_qt_conversion"
TKINTER_DIR="/home/andrc1/camera_system_integrated_final"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
SLAVES_OK=0
SLAVES_RESTARTED=0
SLAVES_FAILED=0

log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $@" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
}

# Check Tkinter service status
check_tkinter_services() {
    local ip=$1
    local video=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active video_stream.service 2>/dev/null" || echo "inactive")
    local capture=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active still_capture.service 2>/dev/null" || echo "inactive")
    echo "$video|$capture"
}

# Ensure Tkinter services are running (stop any Qt services first)
ensure_tkinter_services() {
    local ip=$1
    local name=$2
    
    # Stop Qt services if running
    ssh "$REMOTE_USER@$ip" "sudo systemctl stop gertie-video.service gertie-capture.service 2>/dev/null || true" 2>/dev/null
    ssh "$REMOTE_USER@$ip" "sudo systemctl disable gertie-video.service gertie-capture.service 2>/dev/null || true" 2>/dev/null
    
    # Enable and restart Tkinter services
    ssh "$REMOTE_USER@$ip" "sudo systemctl enable video_stream.service still_capture.service 2>/dev/null || true"
    ssh "$REMOTE_USER@$ip" "sudo systemctl restart video_stream.service still_capture.service"
    
    log "INFO" "$name: Tkinter services restarted"
    ((SLAVES_RESTARTED++))
}

# Process a remote slave
process_slave() {
    local ip=$1
    local name="rep$((${ip##*.} - 200))"
    
    echo -e "${CYAN}━━━ $name ($ip) ━━━${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "$ip" &> /dev/null; then
        echo -e "${RED}✗ $name: Not reachable${NC}"
        log "ERROR" "$name: Not reachable"
        ((SLAVES_FAILED++))
        return 1
    fi
    
    # Check Tkinter service status
    local status=$(check_tkinter_services "$ip")
    IFS='|' read -r video capture <<< "$status"
    
    if [ "$video" = "active" ] && [ "$capture" = "active" ]; then
        echo -e "${GREEN}✓ $name: Tkinter services running (video=$video capture=$capture)${NC}"
        log "INFO" "$name: Services OK (video=$video capture=$capture)"
        ((SLAVES_OK++))
    else
        echo -e "${YELLOW}! $name: Services need restart (video=$video capture=$capture)${NC}"
        ensure_tkinter_services "$ip" "$name"
    fi
}

# Process local slave (rep8 on control1)
process_local() {
    echo -e "${CYAN}━━━ rep8 (local) ━━━${NC}"
    
    local status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
    
    if [ "$status" = "active" ]; then
        echo -e "${GREEN}✓ rep8: local_camera_slave.service running${NC}"
        log "INFO" "rep8: Service OK ($status)"
    else
        echo -e "${YELLOW}! rep8: Restarting local_camera_slave.service${NC}"
        sudo systemctl restart local_camera_slave.service
        log "INFO" "rep8: local_camera_slave.service restarted"
    fi
}

# Main
main() {
    log_section "HYBRID DEPLOYMENT (Qt GUI + Tkinter Slaves)"
    log "INFO" "Qt GUI: $QT_DIR"
    log "INFO" "Tkinter Slaves: $TKINTER_DIR"
    
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  GERTIE Hybrid: Qt GUI + Tkinter Slaves    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Process all remote slaves
    for ip in "${REMOTE_SLAVES[@]}"; do
        process_slave "$ip"
    done
    
    # Process local slave
    process_local
    
    # Summary
    echo ""
    echo -e "${CYAN}━━━ Summary ━━━${NC}"
    echo -e "  OK:        ${GREEN}$SLAVES_OK${NC}"
    echo -e "  Restarted: ${YELLOW}$SLAVES_RESTARTED${NC}"
    echo -e "  Failed:    ${RED}$SLAVES_FAILED${NC}"
    
    log "INFO" "Deployment complete: OK=$SLAVES_OK Restarted=$SLAVES_RESTARTED Failed=$SLAVES_FAILED"
    
    if [ $SLAVES_FAILED -gt 0 ]; then
        echo -e "\n${RED}⚠ Some slaves failed - check connectivity${NC}"
        return 1
    fi
    
    echo -e "\n${GREEN}✓ All slaves ready - run ./run_qt_with_logging.sh${NC}"
}

# Quick status check
if [ "$1" = "--status" ] || [ "$1" = "-s" ]; then
    echo "Checking slave status..."
    for ip in "${REMOTE_SLAVES[@]}"; do
        name="rep$((${ip##*.} - 200))"
        status=$(check_tkinter_services "$ip" 2>/dev/null || echo "unreachable|unreachable")
        IFS='|' read -r v c <<< "$status"
        echo "  $name: video=$v capture=$c"
    done
    local_status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
    echo "  rep8: local=$local_status"
    exit 0
fi

main "$@"
