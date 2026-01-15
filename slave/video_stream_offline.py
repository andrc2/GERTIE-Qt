#!/usr/bin/env python3
"""
OFFLINE FIXED Video Stream Script for rep1-7  
No external dependencies - works in isolated network
Robust device detection using system commands
"""

import os
import io
import json
import time
import socket
import threading
import logging
import datetime
import cv2
import numpy as np
import traceback
import subprocess
import re
from picamera2 import Picamera2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import from config with robust fallback
try:
    import sys
    import os
    sys.path.insert(0, "/home/andrc1/camera_system_integrated_final")
    
    from shared.config import MASTER_IP, VIDEO_PORT, get_slave_ports, HEARTBEAT_PORT
    logging.info("✅ Successfully imported from shared.config")
except ImportError as e:
    logging.warning(f"❌ Failed to import shared.config: {e}")
    # Fallback configuration
    MASTER_IP = "192.168.0.200"
    VIDEO_PORT = 5002
    HEARTBEAT_PORT = 5003
    
    def get_slave_ports(ip: str):
        """Fallback function to get slave ports"""
        if ip == "127.0.0.1" or ip.startswith("127."):
            return {"control": 5011, "video": 5012, "video_control": 5014, "still": 6010, "heartbeat": 5013}
        else:
            return {"control": 5001, "video": 5002, "video_control": 5004, "still": 6000, "heartbeat": 5003}
    
    logging.info("Using fallback configuration")

# Global variables
streaming = False
streaming_lock = threading.Lock()
jpeg_quality = 80

def get_device_name_from_ip():
    """OFFLINE FIXED: Get correct device name without external dependencies"""
    try:
        import socket
        import subprocess
        
        hostname = socket.gethostname()
        local_ip = None
        
        # Method 1: Direct IP command (MOST RELIABLE - no external deps)
        try:
            # Get IP from network interfaces using system commands
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet 192.168.0.' in line and '192.168.0.200' not in line:
                        # Extract IP address
                        parts = line.strip().split()
                        for part in parts:
                            if part.startswith('192.168.0.') and '/' in part:
                                local_ip = part.split('/')[0]
                                if local_ip != '192.168.0.200':  # Skip master IP
                                    logging.info(f"[VIDEO] Method 1 - IP command: {local_ip}")
                                    break
                        if local_ip:
                            break
        except Exception as e:
            logging.warning(f"[VIDEO] Method 1 failed: {e}")
        
        # Method 2: Hostname parsing (ENHANCED - extract rep number)
        if not local_ip:
            try:
                logging.info(f"[VIDEO] Trying hostname parsing for: {hostname}")
                hostname_lower = hostname.lower()
                
                # Try multiple hostname patterns
                if "rep" in hostname_lower:
                    # Extract number after "rep"
                    match = re.search(r'rep(\d+)', hostname_lower)
                    if match:
                        rep_num = int(match.group(1))
                        if 1 <= rep_num <= 7:
                            local_ip = f"192.168.0.20{rep_num}"
                            logging.info(f"[VIDEO] Method 2 - Hostname parsing: {hostname} -> rep{rep_num} -> {local_ip}")
                        elif rep_num == 8:
                            local_ip = "192.168.0.200"
                            logging.info(f"[VIDEO] Method 2 - Hostname parsing: {hostname} -> rep8 -> {local_ip}")
                
                # Try if hostname ends with a number (like "pi1", "control1", etc.)
                if not local_ip:
                    match = re.search(r'(\d+)$', hostname_lower)
                    if match:
                        num = int(match.group(1))
                        if 1 <= num <= 7:
                            local_ip = f"192.168.0.20{num}"
                            logging.info(f"[VIDEO] Method 2b - Number suffix: {hostname} -> {local_ip}")
                            
            except Exception as e:
                logging.warning(f"[VIDEO] Method 2 failed: {e}")
        
        # Method 3: Check /etc/hostname and /etc/hosts
        if not local_ip:
            try:
                # Read /etc/hostname
                with open('/etc/hostname', 'r') as f:
                    system_hostname = f.read().strip().lower()
                    logging.info(f"[VIDEO] System hostname from /etc/hostname: {system_hostname}")
                    
                    if "rep" in system_hostname:
                        match = re.search(r'rep(\d+)', system_hostname)
                        if match:
                            rep_num = int(match.group(1))
                            if 1 <= rep_num <= 7:
                                local_ip = f"192.168.0.20{rep_num}"
                                logging.info(f"[VIDEO] Method 3 - /etc/hostname: {system_hostname} -> {local_ip}")
                                
            except Exception as e:
                logging.warning(f"[VIDEO] Method 3 failed: {e}")
        
        # Method 4: Connect to known slave IPs to test which one we are
        if not local_ip:
            try:
                for test_rep in range(1, 8):
                    test_ip = f"192.168.0.20{test_rep}"
                    try:
                        # Try to bind to a test port on this IP
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        test_sock.bind((test_ip, 0))  # Bind to any available port
                        test_sock.close()
                        local_ip = test_ip
                        logging.info(f"[VIDEO] Method 4 - Bind test: Successfully bound to {local_ip}")
                        break
                    except OSError:
                        # Can't bind to this IP, not us
                        continue
            except Exception as e:
                logging.warning(f"[VIDEO] Method 4 failed: {e}")
        
        # Method 5: Last resort - check default gateway and infer
        if not local_ip:
            try:
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Look for default route to infer our IP
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'src 192.168.0.' in line:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == 'src' and i + 1 < len(parts):
                                    candidate_ip = parts[i + 1]
                                    if candidate_ip.startswith('192.168.0.') and candidate_ip != '192.168.0.200':
                                        local_ip = candidate_ip
                                        logging.info(f"[VIDEO] Method 5 - Route table: {local_ip}")
                                        break
                            if local_ip:
                                break
            except Exception as e:
                logging.warning(f"[VIDEO] Method 5 failed: {e}")
        
        # Final fallback
        if not local_ip:
            logging.error(f"[VIDEO] All methods failed - using default rep8")
            local_ip = "192.168.0.200"  # Default to rep8
        
        logging.info(f"[VIDEO] Final detection - Hostname: {hostname}, IP: {local_ip}")
        
        # FIXED: Precise IP to device mapping
        device_mapping = {
            "192.168.0.201": "rep1",
            "192.168.0.202": "rep2", 
            "192.168.0.203": "rep3",
            "192.168.0.204": "rep4",
            "192.168.0.205": "rep5",
            "192.168.0.206": "rep6",
            "192.168.0.207": "rep7",
            "192.168.0.200": "rep8",  # Master
            "127.0.0.1": "rep8",      # Local
            "localhost": "rep8"       # Local
        }
        
        device_name = device_mapping.get(local_ip, "rep8")
        
        # CRITICAL: Force logging of device detection
        logging.warning(f"[VIDEO] 🆔 DEVICE DETECTION: {local_ip} -> {device_name}")
        logging.warning(f"[VIDEO] 🆔 HOSTNAME: {hostname}")
        
        logging.info(f"[VIDEO] Resolved: {local_ip} -> {device_name}")
        return device_name
            
    except Exception as e:
        logging.error(f"[VIDEO] Error getting device name: {e}")
        return "rep8"  # Fallback

def load_device_settings(device_name):
    """Load settings from correct device-specific file"""
    settings_file = f"/home/andrc1/camera_system_integrated_final/{device_name}_settings.json"
    
    # FIXED: Default settings with correct brightness and transform values
    default_settings = {
        'brightness': 50,           # CRITICAL: Never 0
        'contrast': 50,
        'iso': 100,
        'saturation': 50,
        'white_balance': 'auto',
        'jpeg_quality': 80,
        'fps': 30,
        'resolution': '640x480',
        'crop_enabled': False,
        'crop_x': 0,
        'crop_y': 0,
        'crop_width': 4608,
        'crop_height': 2592,
        'flip_horizontal': False,
        'flip_vertical': False,
        'grayscale': False,
        'rotation': 0
    }
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                
                # CRITICAL: Brightness protection for video stream
                original_brightness = settings.get('brightness', 50)
                if original_brightness == 0:
                    logging.warning(f"[VIDEO] 🚨 BLOCKING brightness=0 for {device_name} - using 50")
                    settings['brightness'] = 50
                elif original_brightness < 10:
                    logging.warning(f"[VIDEO] 🚨 BLOCKING low brightness={original_brightness} for {device_name} - using 50")
                    settings['brightness'] = 50
                
                return settings
        else:
            logging.info(f"[VIDEO] Creating default settings for {device_name}")
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
            
    except Exception as e:
        logging.error(f"[VIDEO] Failed to load settings for {device_name}: {e}")
        logging.info(f"[VIDEO] Using safe default settings for {device_name}")
        return default_settings

def apply_video_transforms(image_array, device_name):
    """Apply video transforms keeping RGB format for correct color display"""
    try:
        settings = load_device_settings(device_name)
        image = image_array.copy()  # Keep RGB format for video stream
        
        # Apply transforms (these are PURE frame operations)
        # 1. Crop
        if settings.get('crop_enabled', False):
            x = max(0, settings.get('crop_x', 0))
            y = max(0, settings.get('crop_y', 0))
            w = max(100, settings.get('crop_width', image.shape[1]))
            h = max(100, settings.get('crop_height', image.shape[0]))
            
            height, width = image.shape[:2]
            x = min(x, width - 100)
            y = min(y, height - 100)
            w = min(w, width - x)
            h = min(h, height - y)
            
            image = image[y:y+h, x:x+w]
        
        # 2. Rotation
        rotation = settings.get('rotation', 0)
        if rotation == 90:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif rotation == 270:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # 3. Flips (keep RGB format for video display)
        if settings.get('flip_horizontal', False):
            image = cv2.flip(image, 1)
        if settings.get('flip_vertical', False):
            image = cv2.flip(image, 0)
        
        # 4. Grayscale (stay in RGB format for video display)
        if settings.get('grayscale', False):
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        return image
        
    except Exception as e:
        logging.error(f"[VIDEO_TRANSFORM] Error for {device_name}: {e}")
        return image_array

def start_video_stream():
    """Start video streaming with enhanced device detection"""
    global streaming, jpeg_quality
    
    device_name = get_device_name_from_ip()
    
    with streaming_lock:
        if streaming:
            logging.warning(f"[VIDEO] {device_name} video stream already running")
            return
        streaming = True

    logging.info(f"🚀 Starting VIDEO stream for {device_name} to {MASTER_IP}:{VIDEO_PORT}")

    picam2 = None
    sock = None
    frame_count = 0
    last_log_time = time.time()
    error_count = 0
    max_errors = 10

    try:
        # Initialize camera
        logging.info(f"[VIDEO] Initializing camera for {device_name}...")
        picam2 = Picamera2()
        
        video_config = picam2.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            controls={"FrameRate": 15}
        )
        picam2.configure(video_config)
        picam2.start()
        
        logging.info(f"✓ {device_name} camera initialized")
        time.sleep(2.0)

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.1)
        
        logging.info(f"✓ {device_name} socket created, streaming to {MASTER_IP}:{VIDEO_PORT}")
        
        start_time = time.time()
        
        while True:
            with streaming_lock:
                if not streaming:
                    logging.info(f"[VIDEO] {device_name} stream stop requested, breaking loop")
                    break
            
            try:
                # Capture frame (RGB888 format from Picamera2)
                frame_rgb = picam2.capture_array()
                
                # Apply transforms keeping RGB format for correct colors
                frame_rgb_transformed = apply_video_transforms(frame_rgb, device_name)
                
                # CRITICAL: Keep RGB format for video stream (correct colors in GUI)
                # Encode as JPEG in RGB format
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 70]
                success, encoded = cv2.imencode(".jpg", frame_rgb_transformed, encode_params)
                
                if not success:
                    logging.warning(f"[VIDEO] {device_name} failed to encode frame")
                    continue
                
                frame_data = encoded.tobytes()
                
                # Check frame size and reduce quality if needed
                if len(frame_data) > 60000:
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
                    success, encoded = cv2.imencode(".jpg", frame_rgb_transformed, encode_params)
                    if success:
                        frame_data = encoded.tobytes()
                
                # Send to master GUI
                try:
                    sock.sendto(frame_data, (MASTER_IP, VIDEO_PORT))
                    error_count = 0
                except socket.timeout:
                    pass
                except socket.error as e:
                    error_count += 1
                    if error_count <= 3:
                        logging.error(f"[VIDEO] {device_name} socket error #{error_count}: {e}")
                    if error_count >= max_errors:
                        logging.error(f"[VIDEO] {device_name} too many socket errors, stopping stream")
                        break
                
                frame_count += 1
                
                # Log stats every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5.0:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    logging.info(f"📊 {device_name}: {fps:.1f} fps, {len(frame_data)} bytes/frame, {frame_count} total frames")
                    last_log_time = current_time
                
                # Frame rate control
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    logging.error(f"[VIDEO] {device_name} error in video loop #{error_count}: {e}")
                if error_count >= max_errors:
                    logging.error(f"[VIDEO] {device_name} too many video loop errors, stopping")
                    break
                time.sleep(0.1)
                
    except Exception as e:
        logging.error(f"[VIDEO] Critical error in {device_name} video streaming: {e}")
        
    finally:
        # Cleanup
        if picam2:
            try:
                picam2.stop()
                picam2.close()
                logging.info(f"✓ {device_name} camera stopped")
            except Exception as e:
                logging.error(f"[VIDEO] {device_name} error stopping camera: {e}")

        if sock:
            try:
                sock.close()
                logging.info(f"✓ {device_name} socket closed")
            except Exception as e:
                logging.error(f"[VIDEO] {device_name} error closing socket: {e}")

        with streaming_lock:
            streaming = False
            
        logging.info(f"🛑 {device_name} video stream stopped")

def stop_video_stream():
    """Stop video streaming"""
    device_name = get_device_name_from_ip()
    
    global streaming
    logging.info(f"[VIDEO] 🛑 Stopping {device_name} video stream...")
    with streaming_lock:
        streaming = False
    
    time.sleep(1.0)
    logging.info(f"[VIDEO] ✅ {device_name} video stream stopped")

def handle_commands():
    """Handle video control commands"""
    device_name = get_device_name_from_ip()
    
    logging.info(f"[VIDEO] Starting {device_name} command handler...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Bind to the video control port
        control_port = 5004  # Video control port for slaves
        sock.bind(("0.0.0.0", control_port))
        logging.info(f"✓ {device_name} command handler listening on port {control_port}")
    except OSError as e:
        logging.error(f"✗ {device_name} failed to bind to port {control_port}: {e}")
        return

    command_count = 0
    
    while True:
        try:
            sock.settimeout(5.0)
            data, addr = sock.recvfrom(1024)
            command = data.decode().strip()
            command_count += 1
            
            logging.info(f"[VIDEO] {device_name} command #{command_count} from {addr}: {command}")

            if command == "START_STREAM":
                logging.info(f"[VIDEO] {device_name} processing START_STREAM command")
                if not streaming:
                    threading.Thread(target=start_video_stream, daemon=True).start()
                else:
                    logging.info(f"[VIDEO] {device_name} stream already running")
                    
            elif command == "STOP_STREAM":
                logging.info(f"[VIDEO] {device_name} processing STOP_STREAM command")
                stop_video_stream()
                
            elif command == "STATUS":
                status = f"STREAMING:{streaming}"
                logging.info(f"[VIDEO] {device_name} status request: {status}")
                
            else:
                logging.warning(f"[VIDEO] {device_name} unknown command: {command}")
                
        except socket.timeout:
            continue
        except Exception as e:
            logging.error(f"[VIDEO] {device_name} error handling command: {e}")

def main():
    """Main video streaming service"""
    device_name = get_device_name_from_ip()
    
    logging.warning(f"[MAIN] 🚀 STARTING OFFLINE FIXED video service for {device_name}")
    logging.warning(f"[MAIN] 🆔 Device identification: {device_name}")
    logging.warning(f"[MAIN] ✅ Offline device detection enabled")
    logging.warning(f"[MAIN] ✅ No external dependencies required")
    
    try:
        # Start command handler
        threading.Thread(target=handle_commands, daemon=True).start()
        
        logging.warning(f"[MAIN] ✅ Video service started for {device_name}")
        
        # Keep main thread alive
        count = 0
        while True:
            time.sleep(30)
            count += 1
            logging.warning(f"[MAIN] 💓 {device_name} video service alive (status #{count})")
            
    except KeyboardInterrupt:
        logging.warning(f"[MAIN] 🛑 Stopping video service for {device_name}")
        stop_video_stream()
    except Exception as e:
        logging.error(f"[MAIN] ❌ Error in video service for {device_name}: {e}")

if __name__ == "__main__":
    main()
