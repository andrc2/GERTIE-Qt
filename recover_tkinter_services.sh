#!/bin/bash
# RECOVERY: Revert to working Tkinter services for captures
# Run this on control1 to restore 8/8 captures

echo "=== GERTIE Recovery: Reverting to Tkinter services ==="
echo ""

SLAVES=(201 202 203 204 205 206 207)

for ip in "${SLAVES[@]}"; do
    name="rep$((ip - 200))"
    echo "--- $name (192.168.0.$ip) ---"
    
    # Stop Qt services
    ssh andrc1@192.168.0.$ip "sudo systemctl stop gertie-video.service gertie-capture.service 2>/dev/null || true"
    ssh andrc1@192.168.0.$ip "sudo systemctl disable gertie-video.service gertie-capture.service 2>/dev/null || true"
    
    # Re-enable and restart Tkinter services (they still exist in /etc/systemd/system)
    ssh andrc1@192.168.0.$ip "sudo systemctl enable video_stream.service still_capture.service"
    ssh andrc1@192.168.0.$ip "sudo systemctl restart video_stream.service still_capture.service"
    
    # Check status
    v=$(ssh andrc1@192.168.0.$ip "systemctl is-active video_stream.service")
    c=$(ssh andrc1@192.168.0.$ip "systemctl is-active still_capture.service")
    echo "  video_stream=$v still_capture=$c"
done

echo ""
echo "=== Recovery Complete ==="
echo "Now run ./run_qt_with_logging.sh to test"
