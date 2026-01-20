#!/bin/bash
# Update Tkinter slaves to use 4:3 aspect ratio (4056x3040)
# This patches camera_system_integrated_final/slave/still_capture.py on rep1-7

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REMOTE_USER="andrc1"
TKINTER_DIR="/home/andrc1/camera_system_integrated_final"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a /home/andrc1/Desktop/updatelog.txt
}

update_slave() {
    local ip=$1
    local name="rep$((ip - 200))"
    
    echo -e "\n${CYAN}━━━ $name (192.168.0.$ip) ━━━${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "192.168.0.$ip" > /dev/null 2>&1; then
        echo -e "  ${RED}✗ Not reachable${NC}"
        return 1
    fi
    
    echo -e "  ${GREEN}✓ Reachable${NC}"
    echo -e "  Updating still_capture.py to 4:3 (4056x3040)..."
    
    # Apply sed replacements via SSH
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "
        cd $TKINTER_DIR/slave
        
        # Backup original
        cp still_capture.py still_capture.py.bak.16x9
        
        # Replace resolution string
        sed -i \"s/'resolution': '4608x2592'/'resolution': '4056x3040'/g\" still_capture.py
        
        # Replace crop dimensions
        sed -i \"s/'crop_width': 4608/'crop_width': 4056/g\" still_capture.py
        sed -i \"s/'crop_height': 2592/'crop_height': 3040/g\" still_capture.py
        
        # Replace still_config sizes - the main capture resolution
        sed -i 's/main={\"size\": (4608, 2592)}/main={\"size\": (4056, 3040)}/g' still_capture.py
        sed -i 's/raw={\"size\": (4608, 2592)}/raw={\"size\": (4056, 3040)}/g' still_capture.py
        
        # Update warning message
        sed -i 's/expected >1MB for 4608x2592/expected >1MB for 4056x3040/g' still_capture.py
        
        echo 'Patch applied'
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ Patched${NC}"
    else
        echo -e "  ${RED}✗ Patch failed${NC}"
        return 1
    fi
    
    # Verify the change
    echo -n "  Verifying: "
    local check=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "grep -c '4056x3040' $TKINTER_DIR/slave/still_capture.py" 2>/dev/null)
    if [ "$check" -ge 2 ]; then
        echo -e "${GREEN}✓ 4056x3040 found $check times${NC}"
    else
        echo -e "${RED}✗ Verification failed (found $check)${NC}"
        return 1
    fi
    
    # Restart still_capture service
    echo -n "  Restarting service: "
    ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "sudo systemctl restart still_capture.service" 2>/dev/null
    sleep 2
    local status=$(ssh -o ConnectTimeout=5 "$REMOTE_USER@192.168.0.$ip" "systemctl is-active still_capture.service" 2>/dev/null)
    if [ "$status" = "active" ]; then
        echo -e "${GREEN}✓ $status${NC}"
        log "[OK] $name: Updated to 4:3 (4056x3040)"
        return 0
    else
        echo -e "${RED}✗ $status${NC}"
        return 1
    fi
}

# Main
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  UPDATE TKINTER SLAVES: 16:9 → 4:3 ASPECT RATIO           ║${NC}"
echo -e "${CYAN}║  Resolution: 4608x2592 → 4056x3040                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"

log "[UPDATE] Starting 4:3 aspect ratio update for Tkinter slaves"

SUCCESS=0
FAILED=0

for ip in 201 202 203 204 205 206 207; do
    if update_slave $ip; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

# Summary
echo ""
echo -e "${CYAN}━━━ SUMMARY ━━━${NC}"
echo -e "  ${GREEN}Success: $SUCCESS${NC}"
echo -e "  ${RED}Failed:  $FAILED${NC}"

log "[UPDATE] Complete: $SUCCESS success, $FAILED failed"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ ALL SLAVES UPDATED TO 4:3${NC}"
    echo -e "${YELLOW}Run: ./run_qt_with_logging.sh to test captures${NC}"
else
    echo ""
    echo -e "${RED}⚠ Some slaves failed${NC}"
fi
