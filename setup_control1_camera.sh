#!/bin/bash
# ============================================================================
# GERTIE Control1 Camera Setup Script
# ============================================================================
# This script configures control1 (rep8 local camera) to prevent PipeWire
# from auto-claiming the camera hardware, which blocks local_camera_slave.
#
# Run this ONCE on control1 after initial setup or OS reinstall.
# Requires sudo privileges and a reboot to take effect.
#
# Usage: sudo ./setup_control1_camera.sh
# ============================================================================

set -e

echo "============================================"
echo "GERTIE Control1 Camera Setup"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    echo "Usage: sudo ./setup_control1_camera.sh"
    exit 1
fi

# Check if this is control1 (has local camera)
if [ ! -e /dev/video0 ]; then
    echo "WARNING: /dev/video0 not found"
    echo "This script is intended for control1 with the HQ camera attached."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Step 1: Disabling PipeWire V4L2 camera module..."
echo "------------------------------------------------"

# Create PipeWire config directory if it doesn't exist
mkdir -p /etc/pipewire/pipewire.conf.d

# Create config to disable V4L2 module (prevents PipeWire from grabbing cameras)
cat > /etc/pipewire/pipewire.conf.d/disable-v4l2.conf << 'EOF'
# GERTIE: Disable PipeWire camera access so local_camera_slave can use it
context.modules = [
    { name = "libpipewire-module-v4l2" args = { } flags = [ "disabled" ] }
]
EOF

echo "✓ Created /etc/pipewire/pipewire.conf.d/disable-v4l2.conf"

echo ""
echo "Step 2: Adding udev rule for IMX477 HQ camera..."
echo "-------------------------------------------------"

# Create udev rule as backup (tells PipeWire not to manage this specific camera)
cat > /etc/udev/rules.d/99-gertie-camera.rules << 'EOF'
# GERTIE: Prevent PipeWire from managing the HQ camera (IMX477)
SUBSYSTEM=="video4linux", ATTR{name}=="*imx477*", ENV{PIPEWIRE_DONT_MANAGE}="1"
SUBSYSTEM=="video4linux", ATTR{name}=="*imx477*", ENV{LIBCAMERA_DONT_MANAGE}="1"
EOF

echo "✓ Created /etc/udev/rules.d/99-gertie-camera.rules"

# Reload udev rules
udevadm control --reload-rules
echo "✓ Reloaded udev rules"

echo ""
echo "Step 3: Enabling local_camera_slave service..."
echo "-----------------------------------------------"

# Enable the service to start on boot
if [ -f /etc/systemd/system/local_camera_slave.service ]; then
    systemctl enable local_camera_slave.service
    echo "✓ Enabled local_camera_slave.service"
else
    echo "⚠ local_camera_slave.service not installed yet"
    echo "  Run sync_to_slaves.sh first, then:"
    echo "  sudo cp local_camera_slave.service /etc/systemd/system/"
    echo "  sudo systemctl enable local_camera_slave.service"
fi

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "IMPORTANT: You must REBOOT for changes to take effect:"
echo ""
echo "    sudo reboot"
echo ""
echo "After reboot:"
echo "  - PipeWire will no longer grab the camera"
echo "  - local_camera_slave.service will start automatically"
echo "  - Run ./run_qt_with_logging.sh to test"
echo ""
echo "To verify camera is free after reboot:"
echo "    sudo lsof /dev/video0"
echo "    (should show only local_camera_slave or nothing)"
echo ""
