#!/usr/bin/env python3
"""
OFFLINE FIXED Still Capture Script for rep1-7
No external dependencies - works in isolated network
Robust device detection using system commands
"""

import os
import io
import json
import socket
import threading
import logging
import datetime
import time
import cv2
import numpy as np
import subprocess
import re
from picamera2 import Picamera2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import shared functions
import sys
sys.path.insert(0, "/home/andrc1/camera_system_integrated_final")

try:
    from shared.config import MASTER_IP, STILL_PORT
    logging.info("✅ Successfully imported from shared.config")
except ImportError as e:
    logging.warning(f"❌ Failed to import shared.config: {e}")
    MASTER_IP = "192.168.0.200"
    STILL_PORT = 6000

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
                                    logging.info(f"[STILL] Method 1 - IP command: {local_ip}")
                                    break
                        if local_ip:
                            break
        except Exception as e:
            logging.warning(f"[STILL] Method 1 failed: {e}")
        
        # Method 2: Hostname parsing (ENHANCED - extract rep number)
        if not local_ip:
            try:
                logging.info(f"[STILL] Trying hostname parsing for: {hostname}")
                hostname_lower = hostname.lower()
                
                # Try multiple hostname patterns
                if "rep" in hostname_lower:
                    # Extract number after "rep"
                    match = re.search(r'rep(\d+)', hostname_lower)
                    if match:
                        rep_num = int(match.group(1))
                        if 1 <= rep_num <= 7:
                            local_ip = f"192.168.0.20{rep_num}"
                            logging.info(f"[STILL] Method 2 - Hostname parsing: {hostname} -> rep{rep_num} -> {local_ip}")
                        elif rep_num == 8:
                            local_ip = "192.168.0.200"
                            logging.info(f"[STILL] Method 2 - Hostname parsing: {hostname} -> rep8 -> {local_ip}")
                
                # Try if hostname ends with a number (like "pi1", "control1", etc.)
                if not local_ip:
                    match = re.search(r'(\d+)$', hostname_lower)
                    if match:
                        num = int(match.group(1))
                        if 1 <= num <= 7:
                            local_ip = f"192.168.0.20{num}"
                            logging.info(f"[STILL] Method 2b - Number suffix: {hostname} -> {local_ip}")
                            
            except Exception as e:
                logging.warning(f"[STILL] Method 2 failed: {e}")
        
        # Method 3: Check /etc/hostname and /etc/hosts
        if not local_ip:
            try:
                # Read /etc/hostname
                with open('/etc/hostname', 'r') as f:
                    system_hostname = f.read().strip().lower()
                    logging.info(f"[STILL] System hostname from /etc/hostname: {system_hostname}")
                    
                    if "rep" in system_hostname:
                        match = re.search(r'rep(\d+)', system_hostname)
                        if match:
                            rep_num = int(match.group(1))
                            if 1 <= rep_num <= 7:
                                local_ip = f"192.168.0.20{rep_num}"
                                logging.info(f"[STILL] Method 3 - /etc/hostname: {system_hostname} -> {local_ip}")
                                
            except Exception as e:
                logging.warning(f"[STILL] Method 3 failed: {e}")
        
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
                        logging.info(f"[STILL] Method 4 - Bind test: Successfully bound to {local_ip}")
                        break
                    except OSError:
                        # Can't bind to this IP, not us
                        continue
            except Exception as e:
                logging.warning(f"[STILL] Method 4 failed: {e}")
        
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
                                        logging.info(f"[STILL] Method 5 - Route table: {local_ip}")
                                        break
                            if local_ip:
                                break
            except Exception as e:
                logging.warning(f"[STILL] Method 5 failed: {e}")
        
        # Final fallback
        if not local_ip:
            logging.error(f"[STILL] All methods failed - using default rep8")
            local_ip = "192.168.0.200"  # Default to rep8
        
        logging.info(f"[STILL] Final detection - Hostname: {hostname}, IP: {local_ip}")
        
        device_mapping = {
            "192.168.0.201": "rep1",
            "192.168.0.202": "rep2", 
            "192.168.0.203": "rep3",
            "192.168.0.204": "rep4",
            "192.168.0.205": "rep5",
            "192.168.0.206": "rep6",
            "192.168.0.207": "rep7",
            "192.168.0.200": "rep8",
            "127.0.0.1": "rep8",
            "localhost": "rep8"
        }
        
        device_name = device_mapping.get(local_ip, "rep8")
        
        # CRITICAL: Force logging of device detection
        logging.warning(f"[STILL] 🆔 DEVICE DETECTION: {local_ip} -> {device_name}")
        logging.warning(f"[STILL] 🆔 HOSTNAME: {hostname}")
        
        return device_name
            
    except Exception as e:
        logging.error(f"[STILL] Error getting device name: {e}")
        return "rep8"

def load_device_settings(device_name):
    """Load settings from correct device-specific file with EXTRA brightness protection"""
    settings_file = f"/home/andrc1/camera_system_integrated_final/{device_name}_settings.json"
    
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
                
                # CRITICAL: Multiple brightness protections for still capture
                original_brightness = settings.get('brightness', 50)
                if original_brightness == 0:
                    logging.warning(f"[STILL] 🚨 BLOCKING brightness=0 for {device_name} - using 50")
                    settings['brightness'] = 50
                elif original_brightness < 10:
                    logging.warning(f"[STILL] 🚨 BLOCKING low brightness={original_brightness} for {device_name} - using 50")
                    settings['brightness'] = 50
                
                # EXTRA: Verify flip settings don't affect brightness
                if settings.get('flip_vertical', False) or settings.get('flip_horizontal', False):
                    if settings.get('brightness', 50) != 50:
                        logging.info(f"[STILL] ✅ Flip enabled with brightness={settings['brightness']} preserved for {device_name}")
                
                return settings
        else:
            logging.info(f"[STILL] Creating default settings for {device_name}")
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
            
    except Exception as e:
        logging.error(f"[STILL] Failed to load settings for {device_name}: {e}")
        logging.info(f"[STILL] Using safe default settings for {device_name}")
        return default_settings

def apply_simple_transforms(image_array, device_name):
    """Apply simple transforms to match video stream (basic version)"""
    try:
        settings = load_device_settings(device_name)
        image = image_array.copy()  # Keep RGB format
        
        logging.info(f"[STILL_TRANSFORM] Applying transforms for {device_name}")
        
        # Apply basic transforms (same as video stream)
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
        
        # 3. Flips (keep RGB format)
        if settings.get('flip_horizontal', False):
            image = cv2.flip(image, 1)
        if settings.get('flip_vertical', False):
            image = cv2.flip(image, 0)
        
        # 4. Grayscale (stay in RGB format)
        if settings.get('grayscale', False):
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        logging.info(f"[STILL_TRANSFORM] ✅ Transforms applied for {device_name}")
        return image
        
    except Exception as e:
        logging.error(f"[STILL_TRANSFORM] Error for {device_name}: {e}")
        return image_array

def capture_still_image():
    """Capture high-resolution still image - SIMPLIFIED to ensure it works"""
    device_name = get_device_name_from_ip()
    
    logging.info(f"[STILL] Starting SIMPLIFIED capture for {device_name}")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/tmp/still_{device_name}_{timestamp}.jpg"
    
    try:
        # Initialize camera with MINIMAL configuration
        picam2 = Picamera2()
        
        # SIMPLE configuration - no complex controls
        # FIXED: Add raw parameter to force full sensor usage (prevents letterboxing)
        still_config = picam2.create_still_configuration(
            main={"size": (2592, 1944)},  # High resolution only
            raw={"size": (4608, 2592)}    # Force full HQ sensor - prevents letterbox crop
        )
        
        picam2.configure(still_config)
        picam2.start()
        
        logging.info(f"[STILL] Camera configured for {device_name}")
        time.sleep(2)  # Let camera settle
        
        # Capture image (RGB format from Picamera2)
        logging.info(f"[STILL] Capturing image for {device_name}")
        image_rgb = picam2.capture_array()
        
        # Apply same transforms as video stream for consistency
        logging.info(f"[STILL] Applying transforms for {device_name} (match video stream)")
        image_rgb_transformed = apply_simple_transforms(image_rgb, device_name)
        
        # Convert RGB to BGR for file saving (cv2.imwrite expects BGR)
        if len(image_rgb_transformed.shape) == 3 and image_rgb_transformed.shape[2] == 3:
            image_bgr = cv2.cvtColor(image_rgb_transformed, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = image_rgb_transformed
        
        logging.info(f"[STILL] ✅ Transforms applied - still should match video preview")
        
        # Save with standard quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
        success = cv2.imwrite(filename, image_bgr, encode_params)
        
        # Clean up camera
        picam2.stop()
        picam2.close()
        
        if success and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            logging.info(f"[STILL] ✅ CAPTURED {device_name}: {filename} ({file_size} bytes)")
            return filename
        else:
            logging.error(f"[STILL] ❌ Failed to save image for {device_name}")
            return None
            
    except Exception as e:
        logging.error(f"[STILL] ❌ Capture error for {device_name}: {e}")
        logging.error(f"[STILL] Exception details: {str(e)}")
        try:
            if 'picam2' in locals():
                picam2.stop()
                picam2.close()
        except:
            pass
        return None

def send_still_image(filename):
    """Send still image to master GUI"""
    device_name = get_device_name_from_ip()
    
    for attempt in range(3):
        try:
            logging.info(f"[STILL] 🔄 Sending {device_name} image to {MASTER_IP}:{STILL_PORT} (attempt {attempt + 1}/3)")
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)
                s.connect((MASTER_IP, STILL_PORT))
                
                with open(filename, 'rb') as f:
                    data = f.read()
                    s.sendall(data)
                    
                logging.info(f"[STILL] ✅ Sent {len(data)} bytes from {device_name}")
                
                # Clean up temp file
                try:
                    os.remove(filename)
                    logging.info(f"[STILL] 🗑️ Cleaned up temp file for {device_name}")
                except:
                    pass
                    
                return True
                    
        except FileNotFoundError:
            logging.error(f"[STILL] File not found for {device_name}: {filename}")
            return False
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            logging.error(f"[STILL] Connection error for {device_name}: {e}")
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            logging.error(f"[STILL] Send error for {device_name}: {e}")
            return False
    
    logging.error(f"[STILL] Failed to send image from {device_name} after 3 attempts")
    return False

def handle_still_requests():
    """Handle still capture requests with enhanced device detection"""
    device_name = get_device_name_from_ip()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Use consistent device detection for port assignment
        if device_name == "rep8":
            still_port = 6010  # Local camera
        else:
            still_port = 6000  # Slave cameras (rep1-7)
        
        logging.warning(f"[STILL] 🚀 STARTING {device_name} on port {still_port}")
        
        sock.bind(("0.0.0.0", still_port))
        logging.warning(f"[STILL] ✅ {device_name} BOUND to port {still_port}")
        
    except OSError as e:
        logging.error(f"[STILL] ❌ Failed to bind {device_name} to port {still_port}: {e}")
        logging.error(f"[STILL] This usually means another service is using the port")
        return

    logging.warning(f"[STILL] 🎯 {device_name} READY - Waiting for CAPTURE_STILL commands")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            command = data.decode().strip()
            logging.warning(f"[STILL] 📨 {device_name} received command: {command} from {addr}")

            if command == "CAPTURE_STILL":
                logging.warning(f"[STILL] ✅ {device_name} processing CAPTURE_STILL command")
                # Process in separate thread to avoid blocking
                def capture_and_send():
                    try:
                        logging.warning(f"[STILL] 🚀 {device_name} starting capture process")
                        filename = capture_still_image()
                        if filename:
                            logging.warning(f"[STILL] ✅ {device_name} captured: {filename}")
                            success = send_still_image(filename)
                            if success:
                                logging.warning(f"[STILL] ✅ {device_name} sent image successfully")
                            else:
                                logging.error(f"[STILL] ❌ {device_name} failed to send image")
                        else:
                            logging.error(f"[STILL] ❌ {device_name} failed to capture image")
                    except Exception as e:
                        logging.error(f"[STILL] ❌ {device_name} exception in capture: {e}")
                
                threading.Thread(target=capture_and_send, daemon=True).start()
                logging.warning(f"[STILL] 📤 {device_name} capture thread started")
            else:
                logging.warning(f"[STILL] ❓ {device_name} unknown command: {command}")
                    
        except Exception as e:
            logging.error(f"[STILL] ❌ {device_name} error handling request: {e}")

def main():
    """Main still capture service with enhanced device detection"""
    device_name = get_device_name_from_ip()
    
    logging.warning(f"[MAIN] 🚀 STARTING OFFLINE FIXED still service for {device_name}")
    logging.warning(f"[MAIN] 🆔 Device identification: {device_name}")
    logging.warning(f"[MAIN] ✅ Offline device detection enabled")
    logging.warning(f"[MAIN] ✅ No external dependencies required")
    logging.warning(f"[MAIN] ✅ Enhanced error logging enabled")
    
    try:
        # Start still request handler
        threading.Thread(target=handle_still_requests, daemon=True).start()
        
        logging.warning(f"[MAIN] ✅ Still service started for {device_name}")
        
        # Keep main thread alive with enhanced monitoring
        count = 0
        while True:
            time.sleep(30)  # More frequent status updates
            count += 1
            logging.warning(f"[MAIN] 💓 {device_name} still service alive (status #{count})")
            
    except KeyboardInterrupt:
        logging.warning(f"[MAIN] 🛑 Stopping still service for {device_name}")
    except Exception as e:
        logging.error(f"[MAIN] ❌ Error in still service for {device_name}: {e}")

if __name__ == "__main__":
    main()
