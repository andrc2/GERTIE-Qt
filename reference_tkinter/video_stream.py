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
jpeg_quality = 35  # Balanced quality/size - improved from 10 (too low) but still UDP-safe (~8-12KB frames)

def get_device_name_from_ip():
    """SIMPLIFIED: Get correct device name with robust fallback"""
    try:
        hostname = socket.gethostname()
        local_ip = None
        
        # Method 1: Direct network interface check (Most reliable)
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet 192.168.0.2' in line and not '192.168.0.200' in line:
                        # Extract IP address like "192.168.0.201/24"
                        parts = line.strip().split()
                        for part in parts:
                            if part.startswith('192.168.0.2') and '/' in part:
                                local_ip = part.split('/')[0]
                                break
                        if local_ip:
                            break
            logging.info(f"[VIDEO] Method 1 detected: {local_ip}")
        except Exception as e:
            logging.warning(f"[VIDEO] Method 1 failed: {e}")
        
        # Method 2: Hostname to rep number extraction
        if not local_ip:
            try:
                hostname_lower = hostname.lower()
                if "rep" in hostname_lower:
                    import re
                    match = re.search(r'rep(\d+)', hostname_lower)
                    if match:
                        rep_num = int(match.group(1))
                        if 1 <= rep_num <= 7:
                            local_ip = f"192.168.0.20{rep_num}"
                        elif rep_num == 8:
                            local_ip = "192.168.0.200"
                        logging.info(f"[VIDEO] Method 2 detected: {hostname} -> {local_ip}")
            except Exception as e:
                logging.warning(f"[VIDEO] Method 2 failed: {e}")
        
        # Method 3: IP binding test (try to bind to each IP)
        if not local_ip:
            try:
                for test_rep in range(1, 8):
                    test_ip = f"192.168.0.20{test_rep}"
                    try:
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        test_sock.bind((test_ip, 0))
                        test_sock.close()
                        local_ip = test_ip
                        logging.info(f"[VIDEO] Method 3 detected: {local_ip}")
                        break
                    except OSError:
                        continue
            except Exception as e:
                logging.warning(f"[VIDEO] Method 3 failed: {e}")
        
        # Fallback to rep8 if all methods fail
        if not local_ip:
            logging.error(f"[VIDEO] All detection methods failed, defaulting to rep8")
            local_ip = "192.168.0.200"
        
        # Simple IP to device mapping
        device_mapping = {
            "192.168.0.201": "rep1", "192.168.0.202": "rep2", "192.168.0.203": "rep3",
            "192.168.0.204": "rep4", "192.168.0.205": "rep5", "192.168.0.206": "rep6",
            "192.168.0.207": "rep7", "192.168.0.200": "rep8", "127.0.0.1": "rep8"
        }
        
        device_name = device_mapping.get(local_ip, "rep8")
        
        # CRITICAL: Log final detection result
        logging.warning(f"[VIDEO] 🆔 FINAL DETECTION: {local_ip} -> {device_name} (hostname: {hostname})")
        
        return device_name
            
    except Exception as e:
        logging.error(f"[VIDEO] Error in device detection: {e}")
        return "rep8"

def load_device_settings(device_name):
    """Load settings from correct device-specific file - FIXED BRIGHTNESS SCALE"""
    settings_file = f"/home/andrc1/camera_system_integrated_final/{device_name}_settings.json"
    
    # FIXED: Default settings with correct GUI brightness scale
    default_settings = {
        'brightness': 0,            # FIXED: GUI scale (-50 to +50, 0 = neutral)
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
            
            # CRITICAL FIX: Migrate brightness from old scale if needed
            brightness = settings.get('brightness', 0)
            if brightness > 50:  # Old scale (0-100)
                logging.warning(f"[BRIGHTNESS_FIX] {device_name}: brightness {brightness} (old scale) → 0 (GUI neutral)")
                settings['brightness'] = 0
            elif brightness == 50:  # Old neutral value
                logging.warning(f"[BRIGHTNESS_FIX] {device_name}: brightness 50 (old neutral) → 0 (GUI neutral)")
                settings['brightness'] = 0
            elif not (-50 <= brightness <= 50):  # Invalid range
                logging.warning(f"[BRIGHTNESS_FIX] {device_name}: brightness {brightness} (invalid) → 0 (GUI neutral)")
                settings['brightness'] = 0
                
            logging.info(f"[SETTINGS] Loaded {device_name}: brightness={settings.get('brightness', 0)} (GUI scale)")
            return settings
        else:
            logging.info(f"[SETTINGS] Creating default settings file for {device_name}")
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings
            
    except Exception as e:
        logging.error(f"[SETTINGS] Failed to load settings for {device_name}: {e}")
        return default_settings

def save_device_settings(device_name, settings):
    """Save settings to correct device-specific file"""
    try:
        settings_file = f"/home/andrc1/camera_system_integrated_final/{device_name}_settings.json"
        temp_file = f"{settings_file}.tmp"
        
        # Note: brightness=0 is valid (neutral on GUI scale -50 to +50)
        
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        with open(temp_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        os.rename(temp_file, settings_file)
        logging.info(f"[SETTINGS] Saved {device_name}: brightness={settings.get('brightness', 0)}")
        return True
        
    except Exception as e:
        logging.error(f"[SETTINGS] Failed to save settings for {device_name}: {e}")
        return False

def apply_frame_transforms(image_array, device_name):
    """Apply ONLY frame transforms - never affects camera hardware"""
    try:
        settings = load_device_settings(device_name)
        
        # FIXED: Keep RGB format for GUI display (no BGR conversion)
        # GUI expects RGB data, so red objects appear red (not blue)
        image = image_array.copy()
        
        logging.info(f"[TRANSFORM] {device_name}: Processing in RGB format for correct colors")
        
        # Apply transforms in order: crop -> rotation -> flips -> grayscale
        
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
        
        # 3. Flips - THESE NEVER AFFECT CAMERA BRIGHTNESS
        if settings.get('flip_horizontal', False):
            image = cv2.flip(image, 1)
        if settings.get('flip_vertical', False):
            image = cv2.flip(image, 0)
        
        # 4. Grayscale (keep RGB format)
        if settings.get('grayscale', False):
            if len(image.shape) == 3:
                # Convert to grayscale but stay in RGB format
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        logging.info(f"[TRANSFORM] {device_name}: ✅ RGB format preserved - red will appear RED")
        return image
        
    except Exception as e:
        logging.error(f"[TRANSFORM] Error for {device_name}: {e}")
        # Fallback: at minimum convert RGB to BGR
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            return cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        return image_array

def build_camera_controls(device_name):
    """Build ONLY camera hardware controls - MINIMAL APPROACH like rep8"""
    try:
        settings = load_device_settings(device_name)
        
        logging.info(f"[CAMERA] Building MINIMAL controls for {device_name} (matching rep8)")
        
        # MATCH REP8: Only set frame rate, let camera handle the rest
        controls = {"FrameRate": settings.get('fps', 30)}
        
        # DON'T set brightness, contrast, saturation, etc. initially
        # Rep8 doesn't set these and works perfectly
        # Let the camera use its defaults like rep8 does
        
        logging.info(f"[CAMERA] Using MINIMAL controls like rep8: {controls}")
        return controls
        
        # Note: WYSIWYG handled by raw sensor config in create_video_configuration
        # No need to set ScalerCrop here - full sensor usage forced via raw parameter
        
        # Apply brightness to camera hardware - ALWAYS set with correct conversion
        brightness = settings.get('brightness', 0)  # GUI scale: -50 to +50, 0 = neutral
        
        # Convert GUI scale to libcamera: GUI -50→+50 becomes libcamera 0.0→2.0 where 1.0 = neutral
        libcam_brightness = (brightness + 50) / 50.0  # GUI 0 → libcamera 1.0 (neutral)
        controls["Brightness"] = libcam_brightness
        logging.info(f"[CAMERA] Hardware brightness for {device_name}: GUI={brightness} → libcamera={libcam_brightness:.2f} (1.0=neutral)")
        
        # Other camera controls
        contrast = settings.get('contrast', 50)
        if contrast != 50:
            controls["Contrast"] = contrast / 50.0
            
        saturation = settings.get('saturation', 50)
        if saturation != 50:
            controls["Saturation"] = saturation / 50.0
        
        iso = settings.get('iso', 100)
        if iso != 100:
            controls["AnalogueGain"] = iso / 100.0
        
        # White balance
        wb_mode = settings.get('white_balance', 'auto')
        if wb_mode == 'auto':
            controls["AwbEnable"] = True
        else:
            controls["AwbEnable"] = False
            wb_gains = {
                'daylight': (1.5, 1.2),
                'cloudy': (1.8, 1.0),
                'tungsten': (1.0, 2.0),
                'fluorescent': (1.8, 1.5)
            }
            if wb_mode in wb_gains:
                controls["ColourGains"] = wb_gains[wb_mode]
        
        # IMPORTANT: NO flip, rotation, crop, or grayscale in camera controls
        # These are handled in apply_frame_transforms()
        
        logging.info(f"[CAMERA] Controls for {device_name}: {len(controls)} hardware settings")
        return controls
        
    except Exception as e:
        logging.warning(f"[CAMERA] Error building controls for {device_name}: {e}")
        return {"FrameRate": 30}

def get_video_resolution(device_name):
    """Get video resolution from device settings"""
    try:
        settings = load_device_settings(device_name)
        resolution_str = settings.get('resolution', '640x480')
        width, height = map(int, resolution_str.split('x'))
        logging.info(f"[VIDEO] Resolution for {device_name}: {width}x{height}")
        return (width, height)
    except Exception as e:
        logging.warning(f"[VIDEO] Error getting resolution for {device_name}: {e}")
        return (640, 480)

def start_stream():
    """FIXED: Video stream with completely separated camera controls and frame transforms"""
    global streaming, jpeg_quality
    
    with streaming_lock:
        if streaming:
            logging.warning("[VIDEO] Stream already running")
            return
        streaming = True

    device_name = get_device_name_from_ip()
    logging.info(f"[VIDEO] 🚀 Starting FIXED stream for {device_name}")
    logging.info(f"[VIDEO] ✅ Camera controls and frame transforms are completely separated")

    picam2 = None
    sock = None

    try:
        # Initialize camera
        picam2 = Picamera2()
        
        # Get configuration with separated concerns
        resolution = get_video_resolution(device_name)
        camera_controls = build_camera_controls(device_name)
        
        logging.info(f"[VIDEO] Camera config for {device_name}:")
        logging.info(f"[VIDEO] - Resolution: {resolution}")
        logging.info(f"[VIDEO] - Hardware controls: {camera_controls}")
        logging.info(f"[VIDEO] - Frame transforms: Applied per-frame separately")
        
        # Configure camera with ONLY hardware controls
        # WYSIWYG FIX v2: Use raw (sensor) config to force full sensor usage
        video_config = picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"},
            raw={"size": (4608, 2592)},  # Force full HQ sensor - prevents center crop
            controls=camera_controls
        )
        logging.info(f"[VIDEO] WYSIWYG v2: Using full sensor (4608x2592) → scaled to {resolution}")
        picam2.configure(video_config)
        picam2.start()
        
        # MATCH REP8: Don't set controls after start
        # Rep8 doesn't call set_controls and works perfectly
        # Let the camera use its auto-exposure and defaults
        # picam2.set_controls(camera_controls)  # COMMENTED OUT to match rep8
        logging.info(f"[VIDEO] ✅ Camera started with MINIMAL controls (matching rep8)")
        
        logging.info(f"[VIDEO] ✅ Camera hardware initialized for {device_name}")
        time.sleep(2.0)
        
        # Setup UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        
        logging.info(f"[VIDEO] 📡 Streaming to {MASTER_IP}:{VIDEO_PORT} for {device_name}")
        
        # Main streaming loop
        frame_count = 0
        last_time = time.time()
        
        while True:
            with streaming_lock:
                if not streaming:
                    logging.info("[VIDEO] Stream stop requested")
                    break
            
            try:
                # Capture frame from camera (RGB format from Picamera2)
                frame_rgb = picam2.capture_array()
                
                # Apply frame transforms (includes RGB→BGR conversion)
                frame_bgr = apply_frame_transforms(frame_rgb, device_name)
                
                # Encode as JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
                success, encoded = cv2.imencode(".jpg", frame_bgr, encode_params)
                
                if success:
                    frame_data = encoded.tobytes()
                    try:
                        sock.sendto(frame_data, (MASTER_IP, VIDEO_PORT))
                    except socket.error as e:
                        if frame_count % 100 == 0:  # Log errors sparingly
                            logging.warning(f"[VIDEO] Socket error: {e}")
                    
                    # Performance monitoring
                    frame_count += 1
                    if frame_count % 300 == 0:  # Every 10 seconds at 30fps
                        current_time = time.time()
                        actual_fps = 300 / (current_time - last_time)
                        logging.info(f"[VIDEO] {device_name}: {actual_fps:.1f} fps, {len(frame_data)} bytes/frame")
                        last_time = current_time
                
                # Frame rate control removed - let camera run at native FPS (30)
                # Display throttling handled by master GUI
                
            except Exception as e:
                logging.error(f"[VIDEO] Error in streaming loop for {device_name}: {e}")
                break
                
    except Exception as e:
        logging.error(f"[VIDEO] Critical error for {device_name}: {e}")
        
    finally:
        # Cleanup
        if picam2:
            try:
                picam2.stop()
                picam2.close()
                logging.info(f"[VIDEO] Camera stopped for {device_name}")
            except:
                pass
                
        if sock:
            try:
                sock.close()
            except:
                pass
                
        with streaming_lock:
            streaming = False
        
        logging.info(f"[VIDEO] Stream stopped for {device_name}")

def stop_stream():
    """Stop video streaming"""
    global streaming
    
    with streaming_lock:
        if not streaming:
            logging.info("[VIDEO] Stream not running")
            return
        streaming = False
    
    logging.info("[VIDEO] Stream stop requested")

def restart_stream():
    """Restart video stream with fresh settings"""
    device_name = get_device_name_from_ip()
    logging.info(f"[VIDEO] 🔄 Restarting stream for {device_name}...")
    
    stop_stream()
    time.sleep(3.0)  # Allow complete stop
    
    logging.info(f"[VIDEO] 🚀 Starting new stream for {device_name}")
    threading.Thread(target=start_stream, daemon=True).start()
    
    time.sleep(1.0)
    logging.info(f"[VIDEO] ✅ Stream restarted for {device_name}")

def handle_video_commands():
    """Handle video commands with FIXED settings processing"""
    global streaming, jpeg_quality
    
    device_name = get_device_name_from_ip()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        ports = get_slave_ports(local_ip)
        video_control_port = ports['video_control']
        
        sock.bind(("0.0.0.0", video_control_port))
        logging.info(f"[VIDEO] Command handler for {device_name} on port {video_control_port}")
    except OSError as e:
        logging.error(f"[VIDEO] Failed to bind port for {device_name}: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            command = data.decode().strip()
            logging.info(f"[VIDEO] Command for {device_name}: {command}")

            if command == "START_STREAM":
                if not streaming:
                    threading.Thread(target=start_stream, daemon=True).start()
                
            elif command == "STOP_STREAM":
                stop_stream()
                
            elif command == "RESTART_STREAM_WITH_SETTINGS":
                restart_stream()
                
            elif command.startswith("SET_ALL_SETTINGS_"):
                handle_settings_package_fixed(command, device_name)
                
            elif command.startswith("SET_QUALITY_"):
                try:
                    quality = int(command.split('_')[2])
                    if 20 <= quality <= 100:
                        jpeg_quality = quality
                        logging.info(f"[VIDEO] JPEG quality for {device_name}: {quality}")
                except:
                    logging.error(f"[VIDEO] Invalid quality command: {command}")
            
            elif command == "RESET_TO_FACTORY_DEFAULTS":
                handle_factory_reset_fixed(device_name)
                    
        except Exception as e:
            logging.error(f"[VIDEO] Error handling command for {device_name}: {e}")

def handle_settings_package_fixed(command, device_name):
    """FIXED: Handle settings with brightness protection and proper separation"""
    try:
        json_part = command[17:]  # Remove "SET_ALL_SETTINGS_"
        new_settings = json.loads(json_part)
        
        logging.info(f"[SETTINGS] Processing package for {device_name}: {len(new_settings)} settings")
        
        # Load current settings
        current_settings = load_device_settings(device_name)
        
        # Log brightness BEFORE changes
        brightness_before = current_settings.get('brightness', 50)
        logging.info(f"[SETTINGS] BRIGHTNESS_BEFORE for {device_name}: {brightness_before}")
        
        # Process settings with CRITICAL brightness protection
        camera_changes = []
        transform_changes = []
        
        for key, value in new_settings.items():
            if key in current_settings:
                old_val = current_settings[key]
                
                # FIXED: brightness=0 is valid! It's the GUI neutral value
                # No need to block it anymore
                
                # Apply the setting change
                current_settings[key] = value
                
                # Categorize the change
                if key in ['brightness', 'contrast', 'saturation', 'iso', 'white_balance', 'fps', 'resolution']:
                    camera_changes.append(f"{key}: {old_val}→{value}")
                elif key in ['flip_horizontal', 'flip_vertical', 'rotation', 'crop_enabled', 'crop_x', 'crop_y', 'crop_width', 'crop_height', 'grayscale']:
                    transform_changes.append(f"{key}: {old_val}→{value}")
                else:
                    camera_changes.append(f"{key}: {old_val}→{value}")
        
        # Log brightness AFTER changes
        brightness_after = current_settings.get('brightness', 50)
        logging.info(f"[SETTINGS] BRIGHTNESS_AFTER for {device_name}: {brightness_after}")
        
        # Verify brightness preservation
        if brightness_before != brightness_after:
            logging.error(f"[SETTINGS] ❌ BRIGHTNESS_CHANGED for {device_name}: {brightness_before}→{brightness_after}")
        else:
            logging.info(f"[SETTINGS] ✅ BRIGHTNESS_PRESERVED for {device_name}: {brightness_before}")
        
        # Log categorized changes
        if camera_changes:
            logging.info(f"[SETTINGS] 🔧 CAMERA_CONTROLS for {device_name}: {', '.join(camera_changes)}")
        if transform_changes:
            logging.info(f"[SETTINGS] 🖼️ FRAME_TRANSFORMS for {device_name}: {', '.join(transform_changes)}")
        
        # Save settings
        if save_device_settings(device_name, current_settings):
            logging.info(f"[SETTINGS] ✅ Settings saved for {device_name}")
        else:
            logging.error(f"[SETTINGS] ❌ Failed to save settings for {device_name}")
            return
        
        # CRITICAL: Restart strategy based on change type
        if camera_changes:
            # Camera hardware settings changed - need full restart
            logging.info(f"[SETTINGS] 🔄 Camera controls changed for {device_name} - full restart")
            restart_stream()
        elif transform_changes:
            # Only frame transforms changed - no camera restart needed
            logging.info(f"[SETTINGS] 🖼️ Only transforms changed for {device_name} - no restart needed")
        
        logging.info(f"[SETTINGS] ✅ Package complete for {device_name}")
        
    except Exception as e:
        logging.error(f"[SETTINGS] Error processing package for {device_name}: {e}")

def handle_factory_reset_fixed(device_name):
    """Handle factory reset with FIXED brightness protection"""
    try:
        logging.info(f"[RESET] Factory reset for {device_name}")
        
        # Default settings with CORRECT brightness
        default_settings = {
            'brightness': 0,            # Neutral default (hardware will be explicitly set)
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
        
        if save_device_settings(device_name, default_settings):
            logging.info(f"[RESET] ✅ Factory defaults saved for {device_name}")
            restart_stream()
            logging.info(f"[RESET] ✅ Factory reset complete for {device_name}")
        else:
            logging.error(f"[RESET] ❌ Failed to save factory defaults for {device_name}")
        
    except Exception as e:
        logging.error(f"[RESET] Error in factory reset for {device_name}: {e}")

def send_video_heartbeat():
    """Send heartbeat to master"""
    device_name = get_device_name_from_ip()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            while True:
                try:
                    sock.sendto(b"HEARTBEAT", (MASTER_IP, HEARTBEAT_PORT))
                    time.sleep(1.0)
                except Exception as e:
                    if hasattr(send_video_heartbeat, 'error_count'):
                        send_video_heartbeat.error_count += 1
                    else:
                        send_video_heartbeat.error_count = 1
                    
                    if send_video_heartbeat.error_count <= 3:
                        logging.error(f"[HEARTBEAT] Error for {device_name}: {e}")
                    time.sleep(1.0)
    except Exception as e:
        logging.error(f"[HEARTBEAT] Socket error for {device_name}: {e}")

def initialize_device_settings():
    """Initialize settings for this device on startup"""
    device_name = get_device_name_from_ip()
    try:
        logging.info(f"[INIT] Initializing settings for {device_name}")
        settings = load_device_settings(device_name)
        logging.info(f"[INIT] ✅ Settings initialized for {device_name}: brightness={settings.get('brightness', 50)}")
        return True
    except Exception as e:
        logging.error(f"[INIT] Failed to initialize settings for {device_name}: {e}")
        return False

def main():
    """Main function with device-specific initialization"""
    device_name = get_device_name_from_ip()
    
    logging.info(f"[MAIN] Starting FIXED video service for {device_name}")
    logging.info(f"[MAIN] ✅ Brightness preservation enabled")
    logging.info(f"[MAIN] ✅ RGB/BGR color handling fixed")
    logging.info(f"[MAIN] ✅ Device-specific settings loading")
    
    # Initialize device settings
    if not initialize_device_settings():
        logging.error(f"[MAIN] Failed to initialize settings for {device_name}")
    
    try:
        # Start services
        threading.Thread(target=send_video_heartbeat, daemon=True).start()
        threading.Thread(target=handle_video_commands, daemon=True).start()
        
        logging.info(f"[MAIN] Services started for {device_name}")
        
        # Keep main thread alive
        while True:
            time.sleep(10)
            if hasattr(main, 'status_count'):
                main.status_count += 1
            else:
                main.status_count = 1
            
            if main.status_count % 6 == 0:  # Every minute
                logging.info(f"[MAIN] {device_name} alive - streaming: {streaming}")
            
    except KeyboardInterrupt:
        logging.info(f"[MAIN] Stopping video service for {device_name}")
        stop_stream()
    except Exception as e:
        logging.error(f"[MAIN] Error for {device_name}: {e}")

if __name__ == "__main__":
    main()
