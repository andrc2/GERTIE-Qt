#!/usr/bin/env python3
"""
Shared configuration for camera system
Clean version without circular imports
"""

# Master configuration
MASTER_IP = "192.168.0.200"

# Standard ports
CONTROL_PORT = 5001
VIDEO_PORT = 5002
STILL_PORT = 6000  # FIXED: Still capture on dedicated port 6000 for rep1-7
HEARTBEAT_PORT = 5003

# Standard slave ports  
SLAVE_CONTROL_PORT = 5001
SLAVE_VIDEO_PORT = 5002
SLAVE_STILL_PORT = 6000  # FIXED: Still capture on port 6000 for rep1-7
SLAVE_HEARTBEAT_PORT = 5003

# Optional dedicated video control ports (for video_stream command channel)
SLAVE_VIDEO_CONTROL_PORT = 5004

# Local camera ports (to avoid conflicts)
LOCAL_CONTROL_PORT = 5011
LOCAL_VIDEO_PORT = 5012
LOCAL_STILL_PORT = 6010
LOCAL_HEARTBEAT_PORT = 5013
LOCAL_VIDEO_CONTROL_PORT = 5014

# Slave devices configuration
SLAVES = {
    "rep1": {"ip": "192.168.0.201"},
    "rep2": {"ip": "192.168.0.202"},
    "rep3": {"ip": "192.168.0.203"},
    "rep4": {"ip": "192.168.0.204"},
    "rep5": {"ip": "192.168.0.205"},
    "rep6": {"ip": "192.168.0.206"},
    "rep7": {"ip": "192.168.0.207"},
    "rep8": {"ip": "127.0.0.1", "local": True, "use_slave_scripts": True},  # Uses same slave/*.py as remote cameras
}

# Grid configuration
NUM_ROWS = 2
NUM_COLS = 4  # Updated to accommodate 8 cameras (2x4 grid)

# Directory configuration
IMAGE_DIR = "captured_images"
LOCAL_IMAGE_DIR = "captured_images_local"

def get_slave_ports(slave_ip):
    """Get the appropriate ports for a slave based on IP"""
    # Local camera: any 127.x.x.x loopback OR the master IP (192.168.0.200)
    if slave_ip.startswith("127.") or slave_ip == MASTER_IP:
        return {
            'control': LOCAL_CONTROL_PORT,
            'video': LOCAL_VIDEO_PORT,
            'video_control': LOCAL_VIDEO_CONTROL_PORT,
            'still': LOCAL_STILL_PORT,  # 6010 for local camera
            'heartbeat': LOCAL_HEARTBEAT_PORT
        }
    else:  # Remote slaves
        return {
            'control': SLAVE_CONTROL_PORT,  # 5001
            'video': SLAVE_VIDEO_PORT,      # 5002  
            'video_control': SLAVE_VIDEO_CONTROL_PORT,  # 5004
            'still': SLAVE_STILL_PORT,    # 6000 (FIXED: still capture on port 6000)
            'heartbeat': SLAVE_HEARTBEAT_PORT  # 5003
        }
