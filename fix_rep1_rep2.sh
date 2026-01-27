#!/bin/bash
# GERTIE - Fix rep1 and rep2 capture issues
# Run this on control1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GERTIE - Fix rep1 + rep2 Capture Issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================
# REP1 - Camera hardware lock issue
# ============================================================
echo -e "${YELLOW}━━━ REP1 (192.168.0.201) - Fixing camera lock ━━━${NC}"

if ping -c 1 -W 2 192.168.0.201 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Reachable${NC}"
    
    # Kill any processes using the camera
    echo "  Killing camera processes..."
    ssh andrc1@192.168.0.201 "sudo pkill -f 'libcamera\|picamera\|python.*video_stream\|python.*still_capture'" 2>/dev/null
    sleep 2
    
    # Restart services
    echo "  Restarting services..."
    ssh andrc1@192.168.0.201 "sudo systemctl restart video_stream.service && sudo systemctl restart still_capture.service" 2>/dev/null
    sleep 3
    
    # Check status
    VIDEO=$(ssh andrc1@192.168.0.201 "systemctl is-active video_stream.service" 2>/dev/null)
    CAPTURE=$(ssh andrc1@192.168.0.201 "systemctl is-active still_capture.service" 2>/dev/null)
    echo -e "  Status: video=$VIDEO capture=$CAPTURE"
    
    if [ "$VIDEO" = "active" ] && [ "$CAPTURE" = "active" ]; then
        echo -e "  ${GREEN}✓ REP1 services restarted${NC}"
    else
        echo -e "  ${RED}✗ Services not running properly${NC}"
        echo "  Checking journal for errors..."
        ssh andrc1@192.168.0.201 "journalctl -u video_stream.service -n 5 --no-pager" 2>/dev/null
    fi
else
    echo -e "  ${RED}✗ Not reachable${NC}"
fi

# ============================================================
# REP2 - Check Qt still_capture.py deployment
# ============================================================
echo ""
echo -e "${YELLOW}━━━ REP2 (192.168.0.202) - Checking Qt slave code ━━━${NC}"

if ping -c 1 -W 2 192.168.0.202 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Reachable${NC}"
    
    # Check if Qt still_capture.py exists
    echo "  Checking Qt code path..."
    QT_EXISTS=$(ssh andrc1@192.168.0.202 "test -f /home/andrc1/camera_system_qt_conversion/slave/still_capture.py && echo yes || echo no" 2>/dev/null)
    echo "  Qt still_capture.py exists: $QT_EXISTS"
    
    # Check what path the service is using
    echo "  Checking service configuration..."
    SERVICE_PATH=$(ssh andrc1@192.168.0.202 "grep ExecStart /etc/systemd/system/still_capture.service" 2>/dev/null)
    echo "  Service ExecStart: $SERVICE_PATH"
    
    # Check if shared module exists
    SHARED_EXISTS=$(ssh andrc1@192.168.0.202 "test -d /home/andrc1/camera_system_qt_conversion/shared && echo yes || echo no" 2>/dev/null)
    echo "  shared/ module exists: $SHARED_EXISTS"
    
    # Check PYTHONPATH in service
    PYTHONPATH_SET=$(ssh andrc1@192.168.0.202 "grep PYTHONPATH /etc/systemd/system/still_capture.service" 2>/dev/null)
    echo "  PYTHONPATH: $PYTHONPATH_SET"
    
    # Check service status
    CAPTURE=$(ssh andrc1@192.168.0.202 "systemctl is-active still_capture.service" 2>/dev/null)
    echo "  still_capture.service: $CAPTURE"
    
    # Check for Python errors in journal
    echo ""
    echo "  Recent still_capture errors:"
    ssh andrc1@192.168.0.202 "journalctl -u still_capture.service -n 20 --no-pager 2>/dev/null | grep -i 'error\|exception\|import\|module'" 2>/dev/null || echo "  (no errors found)"
    
    # Restart service
    echo ""
    echo "  Restarting still_capture service..."
    ssh andrc1@192.168.0.202 "sudo systemctl restart still_capture.service" 2>/dev/null
    sleep 2
    
    CAPTURE=$(ssh andrc1@192.168.0.202 "systemctl is-active still_capture.service" 2>/dev/null)
    if [ "$CAPTURE" = "active" ]; then
        echo -e "  ${GREEN}✓ REP2 still_capture service active${NC}"
    else
        echo -e "  ${RED}✗ Service not active${NC}"
    fi
else
    echo -e "  ${RED}✗ Not reachable${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done! Now run ./run_qt_with_logging.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
