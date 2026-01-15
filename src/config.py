#!/usr/bin/env python3
"""
GERTIE Qt - Shared Configuration
Mirrors camera_system_integrated_final/shared/config.py exactly
For protocol compatibility between Qt and Tkinter versions

Author: Andrew Crane / Claude GERTIE Session
Date: 2025-11-28
"""

import logging

# Setup module logging
logger = logging.getLogger(__name__)

# =============================================================================
# MASTER CONFIGURATION
# =============================================================================

MASTER_IP = "192.168.0.200"

# =============================================================================
# STANDARD PORTS (Remote Cameras: rep1-rep7)
# =============================================================================

CONTROL_PORT = 5001          # Command reception
VIDEO_PORT = 5002            # Video stream output
STILL_PORT = 6000            # Still capture (dedicated port)
HEARTBEAT_PORT = 5003        # Heartbeat signals
VIDEO_CONTROL_PORT = 5004    # Video stream command channel

# Slave port aliases (for clarity)
SLAVE_CONTROL_PORT = 5001
SLAVE_VIDEO_PORT = 5002
SLAVE_STILL_PORT = 6000
SLAVE_HEARTBEAT_PORT = 5003
SLAVE_VIDEO_CONTROL_PORT = 5004

# =============================================================================
# LOCAL CAMERA PORTS (rep8 on control1 - avoids conflicts)
# =============================================================================

LOCAL_CONTROL_PORT = 5011
LOCAL_VIDEO_PORT = 5012
LOCAL_STILL_PORT = 6010
LOCAL_HEARTBEAT_PORT = 5013
LOCAL_VIDEO_CONTROL_PORT = 5011  # Same as LOCAL_CONTROL_PORT - local_camera_slave handles all commands on one port

# =============================================================================
# SLAVE DEVICES CONFIGURATION
# =============================================================================

SLAVES = {
    "rep1": {"ip": "192.168.0.201"},
    "rep2": {"ip": "192.168.0.202"},
    "rep3": {"ip": "192.168.0.203"},
    "rep4": {"ip": "192.168.0.204"},
    "rep5": {"ip": "192.168.0.205"},
    "rep6": {"ip": "192.168.0.206"},
    "rep7": {"ip": "192.168.0.207"},
    "rep8": {"ip": "127.0.0.1", "local": True, "use_slave_scripts": True},
}

# =============================================================================
# GRID CONFIGURATION
# =============================================================================

NUM_ROWS = 2
NUM_COLS = 4  # 2x4 grid for 8 cameras

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================

IMAGE_DIR = "captured_images"
LOCAL_IMAGE_DIR = "captured_images_local"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_slave_ports(slave_ip: str) -> dict:
    """
    Get the appropriate ports for a slave based on IP.
    
    Args:
        slave_ip: IP address of the slave device
        
    Returns:
        Dictionary with port mappings for control, video, still, heartbeat
    """
    if slave_ip == "127.0.0.1":  # Local camera (rep8)
        ports = {
            'control': LOCAL_CONTROL_PORT,
            'video': LOCAL_VIDEO_PORT,
            'video_control': LOCAL_VIDEO_CONTROL_PORT,
            'still': LOCAL_STILL_PORT,
            'heartbeat': LOCAL_HEARTBEAT_PORT
        }
        logger.debug(f"[CONFIG] Local camera ports: {ports}")
    else:  # Remote slaves (rep1-rep7)
        ports = {
            'control': SLAVE_CONTROL_PORT,
            'video': SLAVE_VIDEO_PORT,
            'video_control': SLAVE_VIDEO_CONTROL_PORT,
            'still': SLAVE_STILL_PORT,
            'heartbeat': SLAVE_HEARTBEAT_PORT
        }
        logger.debug(f"[CONFIG] Remote camera ports for {slave_ip}: {ports}")
    
    return ports


def get_slave_by_ip(ip: str) -> tuple:
    """
    Get slave name and config by IP address.
    
    Args:
        ip: IP address to look up
        
    Returns:
        Tuple of (name, config_dict) or (None, None) if not found
    """
    for name, config in SLAVES.items():
        if config["ip"] == ip:
            logger.debug(f"[CONFIG] Found slave {name} for IP {ip}")
            return name, config
    logger.warning(f"[CONFIG] No slave found for IP {ip}")
    return None, None


def get_slave_by_name(name: str) -> tuple:
    """
    Get slave IP and config by name.
    
    Args:
        name: Slave name (e.g., "rep1", "rep8")
        
    Returns:
        Tuple of (ip, config_dict) or (None, None) if not found
    """
    if name in SLAVES:
        config = SLAVES[name]
        logger.debug(f"[CONFIG] Found IP {config['ip']} for slave {name}")
        return config["ip"], config
    logger.warning(f"[CONFIG] No slave found with name {name}")
    return None, None


def get_camera_id_from_ip(ip: str) -> int:
    """
    Extract camera ID (1-8) from IP address.
    
    Args:
        ip: IP address (e.g., "192.168.0.203")
        
    Returns:
        Camera ID (1-8) or 8 for local camera
    """
    if ip == "127.0.0.1":
        return 8
    try:
        last_octet = int(ip.split('.')[-1])
        camera_id = last_octet - 200
        if 1 <= camera_id <= 8:
            return camera_id
    except (ValueError, IndexError):
        pass
    logger.warning(f"[CONFIG] Could not determine camera ID for IP {ip}, defaulting to 8")
    return 8


def get_ip_from_camera_id(camera_id: int) -> str:
    """
    Get IP address from camera ID (1-8).
    
    Args:
        camera_id: Camera number (1-8)
        
    Returns:
        IP address string
    """
    if camera_id == 8:
        return "127.0.0.1"
    if 1 <= camera_id <= 7:
        return f"192.168.0.{200 + camera_id}"
    logger.warning(f"[CONFIG] Invalid camera ID {camera_id}, defaulting to rep8")
    return "127.0.0.1"


def is_local_camera(ip: str) -> bool:
    """Check if IP represents the local camera (rep8)."""
    return ip == "127.0.0.1" or ip.startswith("127.")


def get_all_remote_slaves() -> dict:
    """Get all remote (non-local) slaves."""
    return {name: config for name, config in SLAVES.items() 
            if not config.get("local", False)}


def get_all_slave_ips() -> list:
    """Get list of all slave IP addresses."""
    return [config["ip"] for config in SLAVES.values()]


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging(level=logging.INFO, log_file=None):
    """
    Setup logging for GERTIE Qt application.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for log output
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    logger.info(f"[CONFIG] Logging initialized at level {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"[CONFIG] Log file: {log_file}")


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    # Setup logging for test
    setup_logging(level=logging.DEBUG)
    
    print("=" * 60)
    print("GERTIE Qt - Configuration Module Test")
    print("=" * 60)
    
    print(f"\nMaster IP: {MASTER_IP}")
    print(f"\nSlaves ({len(SLAVES)} cameras):")
    for name, config in SLAVES.items():
        ip = config["ip"]
        local = config.get("local", False)
        ports = get_slave_ports(ip)
        print(f"  {name}: {ip} {'(LOCAL)' if local else ''}")
        print(f"    Ports: control={ports['control']}, video={ports['video']}, "
              f"still={ports['still']}, heartbeat={ports['heartbeat']}")
    
    print(f"\nGrid: {NUM_ROWS} rows x {NUM_COLS} cols")
    
    print("\n" + "=" * 60)
    print("Helper Function Tests:")
    print("=" * 60)
    
    # Test get_slave_by_ip
    name, config = get_slave_by_ip("192.168.0.203")
    print(f"\nget_slave_by_ip('192.168.0.203'): {name}")
    
    # Test get_slave_by_name
    ip, config = get_slave_by_name("rep5")
    print(f"get_slave_by_name('rep5'): {ip}")
    
    # Test camera ID conversion
    print(f"\nget_camera_id_from_ip('192.168.0.205'): {get_camera_id_from_ip('192.168.0.205')}")
    print(f"get_camera_id_from_ip('127.0.0.1'): {get_camera_id_from_ip('127.0.0.1')}")
    print(f"get_ip_from_camera_id(3): {get_ip_from_camera_id(3)}")
    print(f"get_ip_from_camera_id(8): {get_ip_from_camera_id(8)}")
    
    # Test is_local_camera
    print(f"\nis_local_camera('192.168.0.201'): {is_local_camera('192.168.0.201')}")
    print(f"is_local_camera('127.0.0.1'): {is_local_camera('127.0.0.1')}")
    
    # Test get_all_remote_slaves
    remote = get_all_remote_slaves()
    print(f"\nRemote slaves: {list(remote.keys())}")
    
    print("\n" + "=" * 60)
    print("✓ Configuration module test complete")
    print("=" * 60)
