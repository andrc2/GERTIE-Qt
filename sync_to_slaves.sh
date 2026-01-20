#!/bin/bash
# GERTIE Qt - Hybrid Quick Sync Script
# Checks Tkinter services on rep1-7, restarts if needed
# Does NOT sync code - use reinstall_hybrid_services.sh for full reinstall

set -e

LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a "$LOG_FILE"
}

# Check and restart remote slave if needed
check_slave() {
    local ip=$1
    local name="rep$((${ip##*.} - 200))"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "$ip" &> /dev/null; then
        echo -e "  ${RED}$name: unreachable ✗${NC}"
        return 1
    fi
    
    # Check service status
    local video=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "inactive")
    local capture=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "inactive")
    
    if [ "$video" = "active" ] && [ "$capture" = "active" ]; then
        echo -e "  ${GREEN}$name: video=$video capture=$capture ✓${NC}"
        return 0
    else
        echo -e "  ${YELLOW}$name: video=$video capture=$capture - restarting...${NC}"
        ssh "$REMOTE_USER@$ip" "sudo systemctl restart video_stream.service" 2>/dev/null || true
        sleep 2
        ssh "$REMOTE_USER@$ip" "sudo systemctl restart still_capture.service" 2>/dev/null || true
        sleep 1
        
        # Verify restart
        video=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "failed")
        capture=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "failed")
        
        if [ "$video" = "active" ] && [ "$capture" = "active" ]; then
            echo -e "  ${GREEN}$name: restarted successfully ✓${NC}"
            log "[OK] $name: Services restarted"
            return 0
        else
            echo -e "  ${RED}$name: restart failed ✗${NC}"
            log "[ERROR] $name: Restart failed (video=$video capture=$capture)"
            return 1
        fi
    fi
}

# Check local camera (rep8)
check_local() {
    local status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
    
    if [ "$status" = "active" ]; then
        echo -e "  ${GREEN}rep8: local=$status ✓${NC}"
        return 0
    else
        echo -e "  ${YELLOW}rep8: local=$status - restarting...${NC}"
        sudo systemctl restart local_camera_slave.service
        sleep 2
        status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "failed")
        if [ "$status" = "active" ]; then
            echo -e "  ${GREEN}rep8: restarted successfully ✓${NC}"
            return 0
        else
            echo -e "  ${RED}rep8: restart failed ✗${NC}"
            return 1
        fi
    fi
}

# Main
main() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  GERTIE Hybrid: Quick Service Check        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    
    log "[SYNC] Starting hybrid service check"
    
    local ok=0
    local fail=0
    
    # Check remote slaves (rep1-7)
    echo -e "${CYAN}Remote Slaves (Tkinter):${NC}"
    for ip in 192.168.0.201 192.168.0.202 192.168.0.203 192.168.0.204 192.168.0.205 192.168.0.206 192.168.0.207; do
        if check_slave "$ip"; then
            ((ok++))
        else
            ((fail++))
        fi
    done
    
    # Check local (rep8)
    echo -e "\n${CYAN}Local Camera (Qt):${NC}"
    if check_local; then
        ((ok++))
    else
        ((fail++))
    fi
    
    # Summary
    echo ""
    echo -e "${CYAN}━━━ Summary ━━━${NC}"
    echo -e "  OK:     ${GREEN}$ok${NC}"
    echo -e "  Failed: ${RED}$fail${NC}"
    
    log "[SYNC] Complete: $ok OK, $fail failed"
    
    if [ $fail -eq 0 ]; then
        echo -e "\n${GREEN}✓ All cameras ready - run ./run_qt_with_logging.sh${NC}"
    else
        echo -e "\n${YELLOW}⚠ Some cameras need attention${NC}"
        echo -e "  Run: ${CYAN}./reinstall_hybrid_services.sh${NC} for full reinstall"
    fi
}

# Status only (no restarts)
if [ "$1" = "--status" ] || [ "$1" = "-s" ]; then
    echo "Camera Status:"
    for ip in 201 202 203 204 205 206 207; do
        name="rep$((ip - 200))"
        v=$(ssh -o ConnectTimeout=2 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active video_stream.service" 2>/dev/null || echo "?")
        c=$(ssh -o ConnectTimeout=2 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active still_capture.service" 2>/dev/null || echo "?")
        [ "$v" = "active" ] && [ "$c" = "active" ] && color=$GREEN || color=$RED
        echo -e "  ${color}$name: video=$v capture=$c${NC}"
    done
    l=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "?")
    [ "$l" = "active" ] && color=$GREEN || color=$RED
    echo -e "  ${color}rep8: local=$l${NC}"
    exit 0
fi

main "$@"
