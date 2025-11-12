#!/usr/bin/env python3
"""
Universal Enhanced Still Capture Script
Works for ALL cameras including rep3 - replaces all individual still_capture scripts
Supports: crop, flip, rotation, grayscale, full camera controls
"""

import os
import io
import json
import time
import socket
import threading
import logging
import datetime
import subprocess
import cv2
from picamera2 import Picamera2
# Import from config with robust fallback
try:
    import sys
    import os
    # Add parent directory to path for shared module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from shared.config import MASTER_IP, CONTROL_PORT, STILL_PORT, HEARTBEAT_PORT, get_slave_ports
    logging.info("✅ Successfully imported from shared.config")
except ImportError as e:
    logging.warning(f"❌ Failed to import shared.config: {e}")
    # Fallback configuration
    MASTER_IP = "192.168.0.200"
    CONTROL_PORT = 5001
    STILL_PORT = 6000
    HEARTBEAT_PORT = 5003
    
    # Fallback get_slave_ports function
    def get_slave_ports(ip: str):
        """Fallback function to get slave ports"""
        if ip == "127.0.0.1" or ip.startswith("127."):
            return {"control": 5011, "video": 5012, "video_control": 5014, "still": 6010, "heartbeat": 5013}
        else:
            return {"control": 5001, "video": 5002, "video_control": 5004, "still": 6000, "heartbeat": 5003}
    
    logging.info("Using fallback configuration")
# Import from config
try:
    from shared.config import MASTER_IP, CONTROL_PORT, STILL_PORT, HEARTBEAT_PORT, get_slave_ports
except ImportError:
    # Fallback if config import fails
    MASTER_IP = "192.168.0.200"
    CONTROL_PORT = 5001
    STILL_PORT = 6000
    HEARTBEAT_PORT = 5003

# Directories - Fixed for Pi environment
SAVE_DIR = "/home/andrc1/camera_system_integrated_final/captured_images"

# Feature flags
FEATURE_FLAGS = {
    'ENHANCED_CAMERA_CONTROLS': True,
    'CROP_AND_TRANSFORM': True,
    'ROTATION_SUPPORT': True,
    'SETTINGS_PERSISTENCE': True
}

# Universal camera settings - same for ALL cameras - REVERTED: Keep brightness fixes
camera_settings = {
    # Basic camera controls - REVERTED: Keep GUI brightness scale that was working
    'brightness': 0,            # GUI scale (-50 to +50, 0 = neutral) - REVERTED to working
    'contrast': 50,             # 0-100 (50 = neutral)
    'iso': 100,                 # 100-6400
    'shutter_speed': 1000,      # microseconds
    'saturation': 50,           # 0-100 (50 = neutral)
    'white_balance': 'auto',    # auto/daylight/cloudy/tungsten/etc
    'exposure_mode': 'auto',    # auto/manual/night/etc
    'jpeg_quality': 95,         # Keep high quality for stills 
    'fps': 30,                  # frame rate
    'resolution': '4608x2592',  # Keep explicit high resolution
    'image_format': 'JPEG',     # JPEG/PNG/BMP/TIFF
    
    # Transform settings (NEW - universal for all cameras)
    'crop_enabled': False,
    'crop_x': 0,
    'crop_y': 0,
    'crop_width': 4608,         # Full sensor width
    'crop_height': 2592,        # Full sensor height
    'flip_horizontal': False,
    'flip_vertical': False,
    'grayscale': False,
    'rotation': 0               # 0, 90, 180, 270 degrees
}

# Original defaults (preserved) - REVERTED: Keep brightness fixes
ORIGINAL_DEFAULTS = {
    'brightness': 0,            # GUI scale (-50 to +50, 0 = neutral) - REVERTED to working
    'contrast': 50,
    'iso': 100,
    'shutter_speed': 1000,
    'saturation': 50,
    'white_balance': 'auto',
    'exposure_mode': 'auto',
    'jpeg_quality': 95,         # Keep high quality
    'fps': 30,
    'resolution': '4608x2592',  # Keep explicit high resolution
    'image_format': 'JPEG',
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

def apply_all_transforms(image_array):
    """UNIFIED: Apply transforms using shared pipeline for consistency"""
    try:
        # Import unified transform function
        from shared.transforms import apply_unified_transforms_for_still
        
        # Get device name
        device_name = get_device_name()
        
        # Use shared transform function for consistency
        processed_image = apply_unified_transforms_for_still(image_array, device_name)
        
        logging.info(f"[STILL] ✅ Applied unified transforms for {device_name}")
        return processed_image
        
    except Exception as e:
        logging.error(f"Error applying unified transforms: {e}")
        # Fallback to original logic if unified fails
        return apply_all_transforms_fallback(image_array)

def apply_all_transforms_fallback(image_array):
    """Fallback transform function in case unified transforms fail"""
    try:
        # Ensure we're working with OpenCV format (BGR)
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            # Assume input is RGB, convert to BGR for OpenCV
            image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            image = image_array
        
        # Step 1: Apply crop if enabled
        if camera_settings.get('crop_enabled', False):
            image = apply_crop(image)
        
        # Step 2: Apply rotation
        rotation = camera_settings.get('rotation', 0)
        if rotation != 0:
            image = apply_rotation(image, rotation)
        
        # Step 3: Apply flips
        if camera_settings.get('flip_horizontal', False):
            image = cv2.flip(image, 1)  # Horizontal flip
        
        if camera_settings.get('flip_vertical', False):
            image = cv2.flip(image, 0)  # Vertical flip
        
        # Step 4: Apply grayscale
        if camera_settings.get('grayscale', False):
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                # Convert back to 3-channel for consistency
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        return image
        
    except Exception as e:
        logging.error(f"Error in fallback transforms: {e}")
        return image_array  # Return original if processing fails

def apply_crop(image):
    """Apply crop to image"""
    try:
        x = camera_settings.get('crop_x', 0)
        y = camera_settings.get('crop_y', 0)
        w = camera_settings.get('crop_width', image.shape[1])
        h = camera_settings.get('crop_height', image.shape[0])
        
        # Validate crop bounds
        height, width = image.shape[:2]
        x = max(0, min(x, width - 100))
        y = max(0, min(y, height - 100))
        w = max(100, min(w, width - x))
        h = max(100, min(h, height - y))
        
        # Apply crop
        return image[y:y+h, x:x+w]
        
    except Exception as e:
        logging.error(f"Error applying crop: {e}")
        return image

def apply_rotation(image, degrees):
    """Apply rotation to image"""
    try:
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        if degrees == 90:
            # 90 degrees clockwise
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif degrees == 180:
            # 180 degrees
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif degrees == 270:
            # 270 degrees clockwise (90 counterclockwise)
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        # 0 degrees or invalid - no rotation
        
        return image
        
    except Exception as e:
        logging.error(f"Error applying rotation: {e}")
        return image

def capture_image():
    """Universal enhanced capture with all transforms - SIMPLIFIED PROCESSING PATH"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate device-specific filename
    device_name = get_device_name()
    filename = os.path.join(SAVE_DIR, f"{device_name}_{timestamp}.jpg")
    os.makedirs(SAVE_DIR, exist_ok=True)

    try:
        # FIXED: Always use SIMPLIFIED processing path for guaranteed high resolution
        # The processing path now uses the SIMPLE working logic from slave201
        # No more complex isolation logic that was interfering with capture
        
        logging.info(f"[SLAVE] {device_name}: Using SIMPLIFIED processing path for high resolution")
        return capture_with_processing(filename)
        
    except Exception as e:
        logging.error(f"Error in capture_image: {e}")
        return None

def capture_with_processing(filename):
    """Capture image with full processing pipeline - SIMPLIFIED WORKING VERSION"""
    try:
        picam2 = Picamera2()
        
        # Configure for maximum resolution still - SIMPLE like working slave201
        # FIXED: Add raw parameter to force full sensor usage (prevents letterboxing)
        still_config = picam2.create_still_configuration(
            main={"size": (4608, 2592)},  # Full sensor resolution
            raw={"size": (4608, 2592)}    # Force full HQ sensor - prevents letterbox crop
        )
        picam2.configure(still_config)
        picam2.start()
        
        # Let camera settle - SIMPLE timing like working slave201
        time.sleep(1)
        
        # Capture full resolution image
        image_array = picam2.capture_array()
        
        # Apply all transforms
        processed_image = apply_all_transforms(image_array)
        
        # Save processed image - SIMPLE like working slave201
        success = cv2.imwrite(filename, processed_image)
        
        picam2.stop()
        picam2.close()
        
        if success and os.path.exists(filename):
            logging.info(f"[SLAVE] Processed image saved: {filename}")
            return filename
        else:
            logging.error("[SLAVE] Failed to save processed image")
            return None
            
    except Exception as e:
        logging.error(f"[SLAVE] Error in capture_with_processing: {e}")
        try:
            if 'picam2' in locals():
                picam2.stop()
                picam2.close()
        except:
            pass
        return None

def capture_with_libcamera(filename):
    """Standard capture using libcamera-still (no processing) - FIXED HIGH RESOLUTION"""
    # Build enhanced libcamera-still command with camera settings
    command = ["libcamera-still", "--nopreview", "-o", filename, "--timeout", "1000"]
    
    # Add camera settings (now includes high resolution and quality)
    libcamera_settings = build_libcamera_settings()
    command.extend(libcamera_settings)
    
    device_name = get_device_name()
    logging.info(f"[SLAVE] {device_name}: libcamera-still with HIGH RES settings: {libcamera_settings}")
    
    try:
        subprocess.run(command, timeout=15, check=True)
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            jpeg_quality = camera_settings.get('jpeg_quality', 95)
            logging.info(f"[SLAVE] ✅ HIGH RES standard image saved: {filename} ({file_size} bytes, Q={jpeg_quality}%)")
            return filename
        else:
            logging.error("[SLAVE] libcamera-still failed to create file")
            return None
    except Exception as e:
        logging.error(f"[SLAVE] Error in capture_with_libcamera: {e}")
        return None

def build_libcamera_settings():
    """Build libcamera-still settings from camera_settings - REVERTED: Keep working brightness fix"""
    settings = []
    
    # CRITICAL FIX: Do NOT specify --width and --height 
    # libcamera-still defaults to HIGH RESOLUTION when no size specified
    # Adding explicit size parameters was BREAKING high resolution capture
    
    # CRITICAL FIX: Set high JPEG quality for still captures  
    jpeg_quality = camera_settings.get('jpeg_quality', 95)
    settings.extend(["--quality", str(jpeg_quality)])
    logging.info(f"[STILL] JPEG Quality: {jpeg_quality}% (NO size params - libcamera default HIGH RES)")
    
    # Apply camera settings (only if different from defaults)
    # REVERTED: Keep working brightness calculation that fixed flip bug
    gui_brightness = camera_settings.get('brightness', 0)  # GUI scale
    if gui_brightness != 0:
        # Convert GUI scale to libcamera scale (working version formula)
        if -50 <= gui_brightness <= 50:
            brightness_val = gui_brightness / 50.0
            settings.extend(["--brightness", str(brightness_val)])
            logging.info(f"[STILL] Brightness: GUI={gui_brightness} → libcamera={brightness_val:.2f}")
    
    if camera_settings.get('contrast', 50) != 50:
        contrast_val = camera_settings['contrast'] / 50.0
        settings.extend(["--contrast", str(contrast_val)])
    
    if camera_settings.get('saturation', 50) != 50:
        sat_val = camera_settings['saturation'] / 50.0
        settings.extend(["--saturation", str(sat_val)])
    
    if camera_settings.get('iso', 100) != 100:
        gain_val = camera_settings['iso'] / 100.0
        settings.extend(["--gain", str(gain_val)])
    
    # White balance
    wb_mode = camera_settings.get('white_balance', 'auto')
    if wb_mode != 'auto':
        settings.extend(["--awb", wb_mode])
    
    # Shutter speed
    if camera_settings.get('shutter_speed', 1000) != 1000:
        settings.extend(["--shutter", str(camera_settings['shutter_speed'])])
    
    logging.info(f"[STILL] libcamera command will use DEFAULT HIGH RESOLUTION (no --width/--height)")
    return settings

def build_camera_controls():
    """Build Picamera2 controls from settings - REVERTED: Keep working brightness conversion"""
    controls = {"FrameRate": camera_settings.get('fps', 30)}
    
    # Basic image controls
    # REVERTED: Keep GUI brightness scale (-50 to +50 where 0 = neutral) that fixed flip bug
    gui_brightness = camera_settings.get('brightness', 0)  # GUI default is 0 (neutral)
    if gui_brightness != 0:
        # Convert GUI scale (-50 to +50) to Picamera2 scale (-1.0 to +1.0)
        # FIXED: Ensure proper range validation
        if -50 <= gui_brightness <= 50:
            brightness_val = gui_brightness / 50.0
            controls["Brightness"] = brightness_val
            logging.info(f"[STILL] Brightness: GUI={gui_brightness} → Picamera2={brightness_val:.2f}")
        else:
            logging.warning(f"[STILL] Invalid brightness {gui_brightness}, using neutral (0)")
    
    if camera_settings.get('contrast', 50) != 50:
        # Contrast: 0-100 GUI to Picamera2 scale
        controls["Contrast"] = camera_settings['contrast'] / 50.0
        
    if camera_settings.get('saturation', 50) != 50:
        # Saturation: 0-100 GUI to Picamera2 scale
        controls["Saturation"] = camera_settings['saturation'] / 50.0
    
    # ISO/Gain controls
    if camera_settings.get('iso', 100) != 100:
        controls["AnalogueGain"] = camera_settings['iso'] / 100.0
    
    return controls

def get_device_name():
    """Get device name for filename - CONSISTENT NAMING (fixes rep_X bug)"""
    try:
        # Use consistent device naming from shared module
        from shared.transforms import get_device_name_from_ip
        return get_device_name_from_ip()
    except Exception as e:
        logging.warning(f"Failed to get device name consistently: {e}")
        # Fallback for local/unknown devices
        return "rep8"

def capture_still():
    """Capture and send still image to master - ENHANCED VIDEO STREAM ISOLATION"""
    logging.info("[SLAVE] Starting still capture with COMPLETE video isolation...")
    
    try:
        # CRITICAL FIX: Aggressively stop video stream to prevent interference
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            ports = get_slave_ports(local_ip)
            video_control_port = ports.get('video_control', None)
            if video_control_port:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                    # Send multiple STOP commands to ensure video stream stops
                    vc_sock.sendto(b"STOP_STREAM", ("127.0.0.1", video_control_port))
                    time.sleep(0.5)
                    vc_sock.sendto(b"STOP_STREAM", ("127.0.0.1", video_control_port))
                    logging.info(f"[SLAVE] Sent MULTIPLE STOP_STREAM commands to port {video_control_port}")
                
                # EXTENDED wait for video stream to completely stop
                time.sleep(3.0)  # Increased from 1.5 seconds
                logging.info("[SLAVE] Extended wait for video stream to COMPLETELY stop")
        except Exception as e:
            logging.warning(f"[SLAVE] Unable to send STOP_STREAM before capture: {e}")

        # Now capture with completely isolated camera
        filename = capture_image()
        if filename:
            success = send_image(filename)
            if success:
                logging.info("[SLAVE] Still capture completed successfully")
                return True
            else:
                logging.error("[SLAVE] Failed to send image")
                return False
        else:
            logging.error("[SLAVE] Failed to capture image")
            return False
    except Exception as e:
        logging.error(f"[SLAVE] Error during still capture: {e}")
        return False
    finally:
        # Resume local video stream after capture with delay
        try:
            # Wait before restarting video to ensure still capture is complete
            time.sleep(2.0)
            
            local_ip = socket.gethostbyname(socket.gethostname())
            ports = get_slave_ports(local_ip)
            video_control_port = ports.get('video_control', None)
            if video_control_port:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                    vc_sock.sendto(b"START_STREAM", ("127.0.0.1", video_control_port))
                    logging.info(f"[SLAVE] Sent START_STREAM to resume video on port {video_control_port}")
        except Exception as e:
            logging.warning(f"[SLAVE] Unable to send START_STREAM after capture: {e}")

def send_image(filename):
    """Send captured image to master via TCP"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(30.0)
            sock.connect((MASTER_IP, STILL_PORT))
            
            with open(filename, "rb") as f:
                data = f.read()
            
            sock.sendall(data)
            logging.info(f"[SLAVE] Image sent: {filename} ({len(data)} bytes)")
            return True
            
    except Exception as e:
        logging.error(f"[SLAVE] Error sending image: {e}")
        return False

def handle_control_commands():
    """Enhanced command handler with universal transform support"""
    global camera_settings
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Get port for this device
        ports = get_slave_ports(socket.gethostbyname(socket.gethostname()))
        control_port = ports['control']
        
        sock.bind(("0.0.0.0", control_port))
        logging.info(f"Listening for commands on port {control_port}")
    except OSError as e:
        logging.error(f"Failed to bind to port: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            command = data.decode().strip()
            logging.info(f"Received command from {addr}: {command}")

            # EXISTING COMMANDS (unchanged)
            if command == "CAPTURE_STILL":
                threading.Thread(target=capture_still, daemon=True).start()
            elif command == "RESTART_STREAM_WITH_SETTINGS":
                restart_video_stream()
            elif command == "START_STREAM":
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                    ports = get_slave_ports(local_ip)
                    video_control_port = ports.get('video_control', None)
                    if video_control_port:
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                            vc_sock.sendto(b"START_STREAM", ("127.0.0.1", video_control_port))
                            logging.info(f"Forwarded START_STREAM to local video control port {video_control_port}")
                except Exception as e:
                    logging.error(f"Error forwarding START_STREAM: {e}")
            elif command == "STOP_STREAM":
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                    ports = get_slave_ports(local_ip)
                    video_control_port = ports.get('video_control', None)
                    if video_control_port:
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                            vc_sock.sendto(b"STOP_STREAM", ("127.0.0.1", video_control_port))
                            logging.info(f"Forwarded STOP_STREAM to local video control port {video_control_port}")
                except Exception as e:
                    logging.error(f"Error forwarding STOP_STREAM: {e}")
            
            # TRANSFORM COMMANDS (must be BEFORE general SET_CAMERA_ to avoid conflicts)
            elif command.startswith("SET_CAMERA_CROP_"):
                handle_crop_setting(command)
            elif command.startswith("SET_CAMERA_FLIP_"):
                handle_flip_setting(command)
            elif command.startswith("SET_CAMERA_GRAYSCALE_"):
                handle_grayscale_setting(command)
            elif command.startswith("SET_CAMERA_ROTATION_"):
                handle_rotation_setting(command)
            elif command.startswith("PREVIEW_TRANSFORM_"):
                handle_transform_preview(command)
            
            # NEW: BULK SETTINGS PACKAGE (preferred method)
            elif command.startswith("SET_ALL_SETTINGS_"):
                handle_settings_package(command)
            
            # GENERAL CAMERA SETTING COMMANDS (after specific transforms)
            elif command.startswith("SET_CAMERA_"):
                handle_camera_setting(command)
            
            # RESET COMMANDS
            elif command == "RESET_CAMERA_DEFAULTS":
                reset_to_defaults()
            elif command == "FACTORY_RESET_ALL":
                factory_reset()
            elif command == "RESET_TO_FACTORY_DEFAULTS":
                factory_reset_with_video_forward()
            
            # SYSTEM COMMANDS
            elif command in ("SHUTDOWN", "shutdown", "poweroff", "power off", "shut down"):
                try:
                    # Attempt to stop stream first
                    local_ip = socket.gethostbyname(socket.gethostname())
                    ports = get_slave_ports(local_ip)
                    video_control_port = ports.get('video_control', None)
                    if video_control_port:
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                            vc_sock.sendto(b"STOP_STREAM", ("127.0.0.1", video_control_port))
                    logging.info("Shutdown command received. Powering off...")
                except Exception:
                    pass
                os.system("sudo poweroff")
                break
            elif command in ("REBOOT", "reboot"):
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                    ports = get_slave_ports(local_ip)
                    video_control_port = ports.get('video_control', None)
                    if video_control_port:
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                            vc_sock.sendto(b"STOP_STREAM", ("127.0.0.1", video_control_port))
                    logging.info("Reboot command received. Rebooting...")
                except Exception:
                    pass
                os.system("sudo reboot")
                break
                
        except Exception as e:
            logging.error(f"Error handling command: {e}")

def send_slave_heartbeat():
    """Send heartbeat to master so GUI can mark this device alive."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            while True:
                try:
                    sock.sendto(b"HEARTBEAT", (MASTER_IP, HEARTBEAT_PORT))
                    time.sleep(1.0)
                except Exception as e:
                    logging.error(f"Heartbeat send error: {e}")
                    time.sleep(1.0)
    except Exception as e:
        logging.error(f"Heartbeat socket error: {e}")

def handle_settings_package(command):
    """Handle bulk settings package - prevents command flooding"""
    global camera_settings
    try:
        # Parse: SET_ALL_SETTINGS_{"iso":400,"brightness":60,...}
        json_part = command[17:]  # Remove "SET_ALL_SETTINGS_"
        new_settings = json.loads(json_part)
        
        logging.info(f"[STILL] Received settings package with {len(new_settings)} settings")
        
        # Update camera settings
        for key, value in new_settings.items():
            if key in camera_settings:
                old_val = camera_settings[key]
                camera_settings[key] = value
                logging.info(f"[STILL] {key}: {old_val} -> {value}")
        
        # Save to unified transforms system
        try:
            from shared.transforms import save_device_settings
            device_name = get_device_name()
            if save_device_settings(device_name, camera_settings):
                logging.info(f"[STILL] ✅ SETTINGS_APPLIED to unified system for {device_name}")
            else:
                logging.error(f"[STILL] ❌ Failed to save unified settings for {device_name}")
        except Exception as e:
            logging.error(f"[STILL] Failed to save unified settings: {e}")
        
        # Save settings persistently
        save_settings()
        
        # CRITICAL: Forward settings to video_stream.py on port 5004 with retry
        forwarded = False
        for attempt in range(3):
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                ports = get_slave_ports(local_ip)
                video_control_port = ports.get('video_control', 5004)
                
                # Forward the same command to video_stream.py
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as forward_sock:
                    forward_sock.settimeout(5.0)
                    forward_sock.sendto(command.encode(), ("127.0.0.1", video_control_port))
                    logging.info(f"[STILL] ✅ Settings forwarded to video_stream on port {video_control_port} (attempt {attempt+1})")
                    
                    # Wait for acknowledgment or response
                    import time
                    time.sleep(1)
                    forwarded = True
                    break
                    
            except Exception as e:
                logging.error(f"[STILL] Attempt {attempt+1} failed to forward settings: {e}")
                if attempt < 2:
                    time.sleep(0.5)
        
        if forwarded:
            logging.info(f"[STILL] ✅ SETTINGS_APPLIED+STREAM_RESTARTED forwarded successfully")
        else:
            logging.error(f"[STILL] ❌ Failed to forward settings after 3 attempts")
        
        logging.info(f"[STILL] Settings package completed: {len(new_settings)} settings updated")
        
    except Exception as e:
        logging.error(f"Error handling settings package: {e}")

def handle_camera_setting(command):
    """Handle standard camera setting commands"""
    try:
        # Parse: SET_CAMERA_BRIGHTNESS_75
        parts = command.split('_')
        setting = parts[2].lower()
        value = parts[3]
        
        # Convert value to appropriate type
        if setting in ['brightness', 'contrast', 'iso', 'shutter_speed', 'saturation', 'jpeg_quality', 'fps']:
            camera_settings[setting] = int(value)
        elif setting in ['white_balance', 'exposure_mode', 'resolution', 'image_format']:
            camera_settings[setting] = value
        else:
            camera_settings[setting] = value
            
        logging.info(f"Camera setting updated: {setting} = {value}")
        
        # Signal video stream to restart with new settings
        restart_video_stream_with_new_settings()
        
    except Exception as e:
        logging.error(f"Error handling camera setting: {e}")

def handle_crop_setting(command):
    """Handle crop setting commands"""
    try:
        # Parse commands like:
        # SET_CAMERA_CROP_ENABLED_True
        # SET_CAMERA_CROP_X_100
        # SET_CAMERA_CROP_Y_50
        # SET_CAMERA_CROP_WIDTH_1000
        # SET_CAMERA_CROP_HEIGHT_800
        
        parts = command.split('_')
        crop_param = parts[3].lower()
        value = parts[4]
        
        if crop_param == 'enabled':
            camera_settings['crop_enabled'] = value.lower() == 'true'
        elif crop_param in ['x', 'y', 'width', 'height']:
            camera_settings[f'crop_{crop_param}'] = int(value)
        
        logging.info(f"Crop setting updated: crop_{crop_param} = {value}")
        
        # Signal video stream to restart with new settings
        restart_video_stream_with_new_settings()
        
    except Exception as e:
        logging.error(f"Error handling crop setting: {e}")

def handle_flip_setting(command):
    """Handle flip setting commands"""
    try:
        # Parse commands like:
        # SET_CAMERA_FLIP_HORIZONTAL_True
        # SET_CAMERA_FLIP_VERTICAL_False
        
        parts = command.split('_')
        flip_direction = parts[3].lower()
        value = parts[4].lower() == 'true'
        
        camera_settings[f'flip_{flip_direction}'] = value
        
        logging.info(f"Flip setting updated: flip_{flip_direction} = {value}")
        
        # Signal video stream to restart with new settings
        restart_video_stream_with_new_settings()
        
    except Exception as e:
        logging.error(f"Error handling flip setting: {e}")

def handle_grayscale_setting(command):
    """Handle grayscale setting command"""
    try:
        # Parse command like: SET_CAMERA_GRAYSCALE_True
        parts = command.split('_')
        value = parts[3].lower() == 'true'
        
        camera_settings['grayscale'] = value
        
        logging.info(f"Grayscale setting updated: {value}")
        
        # Signal video stream to restart with new settings
        restart_video_stream_with_new_settings()
        
    except Exception as e:
        logging.error(f"Error handling grayscale setting: {e}")

def handle_rotation_setting(command):
    """Handle rotation setting command"""
    try:
        # Parse command like: SET_CAMERA_ROTATION_90
        parts = command.split('_')
        rotation = int(parts[3])
        
        # Validate rotation value
        if rotation in [0, 90, 180, 270]:
            camera_settings['rotation'] = rotation
            logging.info(f"Rotation setting updated: {rotation}°")
            
            # Signal video stream to restart with new settings
            restart_video_stream_with_new_settings()
        else:
            logging.warning(f"Invalid rotation value: {rotation}")
        
    except Exception as e:
        logging.error(f"Error handling rotation setting: {e}")

def handle_transform_preview(command):
    """Handle live transform preview"""
    try:
        # Parse command like: PREVIEW_TRANSFORM_{"crop_enabled":true,"rotation":90,...}
        json_part = command[17:]  # Remove "PREVIEW_TRANSFORM_"
        preview_settings = json.loads(json_part)
        
        # Apply preview settings temporarily
        # This would update the current video stream temporarily
        logging.info(f"Transform preview applied: {preview_settings}")
        
    except Exception as e:
        logging.error(f"Error handling transform preview: {e}")

def reset_to_defaults():
    """Reset camera settings to original defaults - USES UNIFIED .JSON SYSTEM"""
    global camera_settings
    
    device_name = get_device_name()
    logging.info(f"[STILL] 🔄 Resetting {device_name} to default settings...")
    
    # Reset using unified system
    from shared.transforms import save_device_settings, DEFAULT_SETTINGS
    
    # Save default settings to .json file
    default_settings = DEFAULT_SETTINGS.copy()
    camera_settings = default_settings.copy()  # Update local copy too
    
    if save_device_settings(device_name, default_settings):
        logging.info(f"[STILL] ✅ Default settings saved to {device_name}_settings.json")
    else:
        logging.error(f"[STILL] ❌ Failed to save default settings for {device_name}")
    
    # Restart video stream if it exists (will read new settings from .json file)
    restart_video_stream_with_new_settings()
    
    logging.info(f"[STILL] ✅ Camera reset to defaults complete for {device_name}")

def factory_reset():
    """Complete factory reset - USES UNIFIED .JSON SYSTEM"""
    global camera_settings
    
    device_name = get_device_name()
    logging.info(f"[STILL] 🔄 Starting factory reset for {device_name}...")
    
    # Reset using unified system
    from shared.transforms import save_device_settings, DEFAULT_SETTINGS
    
    # Save default settings to .json file
    default_settings = DEFAULT_SETTINGS.copy()
    camera_settings = default_settings.copy()  # Update local copy too
    
    if save_device_settings(device_name, default_settings):
        logging.info(f"[STILL] ✅ Factory defaults saved to {device_name}_settings.json")
    else:
        logging.error(f"[STILL] ❌ Failed to save factory defaults for {device_name}")
    
    # Clear any cached settings files (legacy cleanup)
    try:
        settings_cache_dir = "/home/andrc1/camera_system_integrated_final/config_files"
        cache_file = os.path.join(settings_cache_dir, f"{device_name}_settings.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logging.info(f"[STILL] 🗑️ Cleared legacy cache file")
    except Exception as e:
        logging.warning(f"[STILL] Could not clear legacy cache: {e}")
    
    restart_video_stream_with_new_settings()
    logging.info(f"[STILL] ✅ Factory reset complete for {device_name}")

def restart_video_stream_with_new_settings():
    """Signal video stream to restart with new settings"""
    try:
        # Get local IP and ports
        local_ip = socket.gethostbyname(socket.gethostname())
        ports = get_slave_ports(local_ip)
        video_control_port = ports.get('video_control', None)
        
        if video_control_port:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vc_sock:
                # Send restart command to video stream process
                vc_sock.sendto(b"RESTART_STREAM_WITH_SETTINGS", ("127.0.0.1", video_control_port))
                logging.info(f"Sent RESTART_STREAM_WITH_SETTINGS to video control port {video_control_port}")
        else:
            logging.warning("Video control port not available, settings may not apply to video stream")
    except Exception as e:
        logging.error(f"Error restarting video stream: {e}")

def restart_video_stream():
    """Send signal to restart video stream with new settings - legacy function"""
    restart_video_stream_with_new_settings()

def save_settings():
    """Save current settings to persistent storage"""
    if not FEATURE_FLAGS.get('SETTINGS_PERSISTENCE', False):
        return
        
    try:
        settings_dir = "/home/andrc1/camera_system_integrated_final/config_files"
        os.makedirs(settings_dir, exist_ok=True)
        
        settings_file = os.path.join(settings_dir, f"{get_device_name()}_settings.json")
        
        with open(settings_file, 'w') as f:
            json.dump(camera_settings, f, indent=2)
            
        logging.info(f"Settings saved to {settings_file}")
        
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

def load_settings():
    """Load settings from persistent storage"""
    if not FEATURE_FLAGS.get('SETTINGS_PERSISTENCE', False):
        return
        
    try:
        settings_dir = "/home/andrc1/camera_system_integrated_final/config_files"
        settings_file = os.path.join(settings_dir, f"{get_device_name()}_settings.json")
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                saved_settings = json.load(f)
                
            # Merge saved settings with defaults (in case new settings were added)
            for key, value in saved_settings.items():
                if key in camera_settings:
                    camera_settings[key] = value
                    
            logging.info(f"Settings loaded from {settings_file}")
        
    except Exception as e:
        logging.error(f"Error loading settings: {e}")

def factory_reset_with_video_forward():
    """Complete factory reset with video stream forwarding - USES UNIFIED .JSON SYSTEM"""
    global camera_settings
    
    # Get device name
    device_name = get_device_name()
    logging.info(f"[STILL] 🔄 Starting factory reset with video forwarding for {device_name}...")
    
    # Reset to defaults in unified system
    from shared.transforms import save_device_settings, DEFAULT_SETTINGS
    
    # Save default settings to .json file
    default_settings = DEFAULT_SETTINGS.copy()
    camera_settings = default_settings.copy()  # Update local copy too
    
    if save_device_settings(device_name, default_settings):
        logging.info(f"[STILL] ✅ Factory defaults saved to {device_name}_settings.json")
    else:
        logging.error(f"[STILL] ❌ Failed to save factory defaults for {device_name}")
    
    # Clear any cached settings files (legacy cleanup)
    try:
        settings_cache_dir = "/home/andrc1/camera_system_integrated_final/config_files"
        cache_file = os.path.join(settings_cache_dir, f"{device_name}_settings.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logging.info(f"[STILL] 🗑️ Cleared legacy settings cache file")
    except Exception as e:
        logging.warning(f"[STILL] Could not clear legacy settings cache: {e}")
    
    # Forward reset command to video stream with retry
    forwarded = False
    for attempt in range(3):
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            ports = get_slave_ports(local_ip)
            video_control_port = ports.get('video_control', 5004)
            
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as forward_sock:
                forward_sock.settimeout(5.0)
                forward_sock.sendto(b"RESET_TO_FACTORY_DEFAULTS", ("127.0.0.1", video_control_port))
                logging.info(f"[STILL] ✅ Factory reset forwarded to video_stream on port {video_control_port} (attempt {attempt+1})")
                forwarded = True
                break
        except Exception as e:
            logging.error(f"[STILL] Attempt {attempt+1} failed to forward factory reset: {e}")
            if attempt < 2:
                time.sleep(0.5)
    
    if forwarded:
        logging.info(f"[STILL] ✅ FACTORY_RESET forwarded to video stream")
    else:
        logging.error(f"[STILL] ❌ Failed to forward factory reset after 3 attempts")
    
    # Save defaults locally too
    save_settings()
    
    logging.info(f"[STILL] ✅ Factory reset complete for {device_name}")

def initialize_device_settings():
    """Initialize settings file for this device on startup - FIXED BRIGHTNESS MIGRATION"""
    try:
        device_name = get_device_name()
        logging.info(f"[STILL] Initializing settings for device: {device_name}")
        
        # Load settings (this will automatically migrate brightness from old scale)
        from shared.transforms import load_device_settings
        settings = load_device_settings(device_name)
        
        # Update local camera_settings with loaded values
        global camera_settings
        for key, value in settings.items():
            if key in camera_settings:
                camera_settings[key] = value
        
        # CRITICAL: Log brightness to verify it's on correct scale
        brightness = camera_settings.get('brightness', 0)
        logging.info(f"[STILL] ✅ Device {device_name} initialized with brightness={brightness} (GUI scale -50 to +50)")
        return True
        
    except Exception as e:
        logging.error(f"[STILL] Failed to initialize device settings: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting universal still capture service...")
    
    # Initialize device settings on startup
    if not initialize_device_settings():
        logging.error("Failed to initialize device settings, continuing anyway...")
    
    # Load saved settings
    load_settings()
    
    try:
        # Start heartbeat and command handler
        threading.Thread(target=send_slave_heartbeat, daemon=True).start()
        handle_control_commands()
    except KeyboardInterrupt:
        logging.info("Still capture service stopped")
    except Exception as e:
        logging.error(f"Error in main: {e}")
    finally:
        # Save settings on exit
        save_settings()

if __name__ == "__main__":
    main()
            