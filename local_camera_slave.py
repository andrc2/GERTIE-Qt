#!/usr/bin/env python3
"""
COMPLETE FIXED Local Camera Slave Service for control1 (rep8)
✅ Fixed: Syntax errors removed
✅ Fixed: High resolution stills (4608, 2592) 
✅ Fixed: Correct color handling (RGB format for GUI)
✅ Fixed: Working transforms using shared.transforms system
✅ Fixed: Proper stop/capture/restart protocol
"""

import os
import io
import json
import socket
import subprocess
import datetime
import time
import threading
import logging
import sys
import cv2
import numpy as np
from picamera2 import Picamera2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [LOCAL-COMPLETE-FIX] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/local_camera_debug.log')
    ]
)

logging.info("=== LOCAL CAMERA COMPLETE FIXED VERSION STARTING ===")

# Fix Python path to find shared module
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import configuration with better error handling
try:
    from shared.config import (
        LOCAL_CONTROL_PORT, LOCAL_VIDEO_PORT, LOCAL_STILL_PORT,
        LOCAL_HEARTBEAT_PORT, LOCAL_IMAGE_DIR, IMAGE_DIR,
        VIDEO_PORT, STILL_PORT, HEARTBEAT_PORT, MASTER_IP as MASTER_IP_FROM_CONFIG
    )
    logging.info("✓ Loaded local camera configuration")
except ImportError as e:
    logging.error(f"✗ Failed to import config: {e}")
    # Fallback configuration
    LOCAL_CONTROL_PORT = 5011
    LOCAL_VIDEO_PORT = 5012
    LOCAL_STILL_PORT = 6010
    LOCAL_HEARTBEAT_PORT = 5013
    LOCAL_IMAGE_DIR = "captured_images_local"
    IMAGE_DIR = "/home/andrc1/camera_system_integrated_final/captured_images"
    VIDEO_PORT = 5002
    STILL_PORT = 6000
    HEARTBEAT_PORT = 5003
    MASTER_IP_FROM_CONFIG = "127.0.0.1"
    logging.info("Using fallback configuration")

# FIXED: Master IP resolution for local camera
def resolve_master_ip():
    """For local camera (rep8), always use localhost"""
    return "127.0.0.1"

MASTER_IP = resolve_master_ip()
logging.info(f"Final Master IP: {MASTER_IP}")

# Global state
streaming = False
streaming_lock = threading.Lock()
video_thread = None
jpeg_quality = 80
last_heartbeat = 0
HEARTBEAT_INTERVAL = 1.0
HEARTBEAT_TIMEOUT = 5.0

# ARCHITECTURAL FIX: Thread synchronization for Picamera2 instance management
# Prevents "camera is already open" errors by ensuring proper cleanup sequencing
stream_stopped_event = threading.Event()  # Signals streaming thread has fully stopped & closed picam2
capture_complete_event = threading.Event()  # Signals capture is done & picam2 closed, safe to restart stream

# Camera settings (matching working version)
camera_settings = {
    'brightness': 0,        # FIXED: Match GUI default (-50 to +50, 0 = neutral)
    'contrast': 50,
    'iso': 100,
    'shutter_speed': 1000,
    'saturation': 50,
    'white_balance': 'auto',
    'exposure_mode': 'auto',
    'jpeg_quality': 80,
    'fps': 30,
    'resolution': '640x480',
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

def send_local_heartbeat():
    """Enhanced heartbeat with better error handling"""
    global last_heartbeat
    
    logging.info(f"Starting heartbeat service to {MASTER_IP}:{HEARTBEAT_PORT}")
    
    heartbeat_count = 0
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1.0)
                
                heartbeat_msg = b"HEARTBEAT"
                sock.sendto(heartbeat_msg, (MASTER_IP, HEARTBEAT_PORT))
                last_heartbeat = time.time()
                heartbeat_count += 1
                
                if heartbeat_count % 10 == 0:
                    logging.info(f"[LOCAL] Heartbeat #{heartbeat_count} sent to {MASTER_IP}:{HEARTBEAT_PORT}")
            
            time.sleep(HEARTBEAT_INTERVAL)
            
        except Exception as e:
            logging.error(f"[LOCAL] Error sending heartbeat #{heartbeat_count}: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

def apply_safe_transforms(image_array):
    """
    UNIFIED: Apply frame transforms using unified pipeline for local camera (rep8)
    Uses apply_unified_transforms for consistency with other slaves
    """
    try:
        # Import unified transform function
        from shared.transforms import apply_unified_transforms
        
        # Use unified transform function for consistency
        processed_image = apply_unified_transforms(image_array, "rep8")
        
        logging.info(f"[LOCAL] ✅ Applied unified transforms for rep8")
        return processed_image
        
    except Exception as e:
        logging.error(f"[LOCAL] Error applying unified transforms: {e}")
        # Fallback to original logic if unified fails
        return apply_safe_transforms_fallback(image_array)

def apply_safe_transforms_fallback(image_array):
    """
    Fallback transform function for local camera if unified transforms fail
    """
    try:
        logging.info(f"[LOCAL] Using fallback transforms for rep8")
        
        # Load settings for rep8 to apply any configured transforms (WORKING METHOD)
        from shared.transforms import load_device_settings
        settings = load_device_settings("rep8")
        
        # Start with RGB format (same as working version)
        image = image_array.copy()
        
        # Apply transforms if configured (same logic as working version)
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
        
        # 3. Flips (maintain RGB format)
        if settings.get('flip_horizontal', False):
            image = cv2.flip(image, 1)
        if settings.get('flip_vertical', False):
            image = cv2.flip(image, 0)
        
        # 4. Grayscale (stay in RGB format)
        if settings.get('grayscale', False):
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        logging.info(f"[LOCAL] ✅ RGB format preserved with transforms applied")
        return image
        
    except Exception as e:
        logging.error(f"[LOCAL] Error applying transforms: {e}")
        # Fallback: keep original RGB format
        return image_array

def start_local_video_stream():
    """WORKING: Enhanced video streaming with proper RGB color handling"""
    global streaming, jpeg_quality
    
    with streaming_lock:
        if streaming:
            logging.warning("Local video stream already running")
            return
        streaming = True
    
    # ARCHITECTURAL FIX: Clear stop event at stream start (will be set on cleanup)
    stream_stopped_event.clear()
    logging.info(f"[EVENT] stream_stopped_event CLEARED at {time.time():.3f} - starting stream")

    logging.info(f"🚀 Starting LOCAL video stream to {MASTER_IP}:{VIDEO_PORT}")

    picam2 = None
    sock = None
    frame_count = 0
    last_log_time = time.time()
    error_count = 0
    max_errors = 10

    try:
        # Initialize camera (same as working version)
        logging.info("Initializing camera...")
        picam2 = Picamera2()
        
        # WYSIWYG FIX: Use raw (sensor) config to force full sensor usage
        # Matches remote slaves (video_stream.py) - prevents center crop
        video_config = picam2.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            raw={"size": (4608, 2592)},  # Force full HQ sensor - prevents center crop
            controls={"FrameRate": 15}
        )
        logging.info("[LOCAL] WYSIWYG: Using full sensor (4608x2592) → scaled to (640, 480)")
        picam2.configure(video_config)
        picam2.start()
        
        logging.info("✓ Local camera initialized")
        time.sleep(2.0)

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.1)
        
        logging.info(f"✓ Socket created, streaming to {MASTER_IP}:{VIDEO_PORT}")
        
        start_time = time.time()
        
        while True:
            with streaming_lock:
                if not streaming:
                    logging.info("Stream stop requested, breaking loop")
                    break
            
            try:
                # Capture frame (RGB888 format from Picamera2)
                frame_rgb = picam2.capture_array()
                
                # Apply transforms keeping RGB format for correct colors (WORKING METHOD)
                frame_rgb_transformed = apply_safe_transforms(frame_rgb)
                
                # CRITICAL: Keep RGB format for GUI display (same as working version)
                # GUI expects RGB format, so red objects appear red (not blue)
                
                # Encode as JPEG in RGB format (working version method)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 70]
                success, encoded = cv2.imencode(".jpg", frame_rgb_transformed, encode_params)
                
                if not success:
                    logging.warning("Failed to encode frame")
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
                    sock.sendto(frame_data, (MASTER_IP, LOCAL_VIDEO_PORT))
                    error_count = 0
                except socket.timeout:
                    pass
                except socket.error as e:
                    error_count += 1
                    if error_count <= 3:
                        logging.error(f"Socket error #{error_count}: {e}")
                    if error_count >= max_errors:
                        logging.error("Too many socket errors, stopping stream")
                        break
                
                frame_count += 1
                
                # Log stats every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5.0:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    logging.info(f"📊 LOCAL: {fps:.1f} fps, {len(frame_data)} bytes/frame, {frame_count} total frames")
                    last_log_time = current_time
                
                # Frame rate control removed - allow native 30 FPS
                
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    logging.error(f"Error in video loop #{error_count}: {e}")
                if error_count >= max_errors:
                    logging.error("Too many video loop errors, stopping")
                    break
                time.sleep(0.1)
                
    except Exception as e:
        logging.error(f"Critical error in local video streaming: {e}")
        
    finally:
        # Cleanup
        if picam2:
            try:
                picam2.stop()
                picam2.close()
                logging.info("✓ Local camera stopped and closed")
            except Exception as e:
                logging.error(f"Error stopping camera: {e}")

        if sock:
            try:
                sock.close()
                logging.info("✓ Local socket closed")
            except Exception as e:
                logging.error(f"Error closing socket: {e}")

        with streaming_lock:
            streaming = False
        
        # ARCHITECTURAL FIX: Signal that Picamera2 cleanup is complete
        # This allows capture_local_still() to safely create new Picamera2 instance
        stream_stopped_event.set()
        logging.info(f"[EVENT] stream_stopped_event SET at {time.time():.3f} - Picamera2 fully closed")
        logging.info("✓ Stream cleanup complete - Picamera2 closed and event signaled")
            
        logging.info("🛑 Local video stream stopped")

def stop_local_video_stream():
    """Properly stop the local video stream"""
    global streaming
    
    logging.info("[LOCAL] 🛑 Stopping local video stream...")
    with streaming_lock:
        streaming = False
    
    time.sleep(1.0)
    logging.info("[LOCAL] ✅ Local video stream stopped")

def capture_local_still():
    """ARCHITECTURAL FIX: Proper thread synchronization for Picamera2 instance management"""
    global streaming
    
    logging.info("[LOCAL] Starting proper still capture protocol with thread synchronization...")
    
    was_streaming = False
    
    # Step 1: Stop video stream to free the camera
    with streaming_lock:
        was_streaming = streaming
        if streaming:
            logging.info("[LOCAL] Step 1: Stopping video stream for dedicated still capture...")
            streaming = False
            # Clear the event before waiting - will be set by streaming thread cleanup
            stream_stopped_event.clear()
            logging.info(f"[EVENT] stream_stopped_event CLEARED at {time.time():.3f}")
    
    if was_streaming:
        # ARCHITECTURAL FIX: Wait for Event instead of blind sleep
        # This ensures streaming thread has ACTUALLY stopped and closed Picamera2
        wait_start = time.time()
        logging.info(f"[EVENT-WAIT] Waiting for stream_stopped_event (timeout=10s) at {wait_start:.3f}...")
        event_received = stream_stopped_event.wait(timeout=10.0)  # 10s max wait
        wait_elapsed = time.time() - wait_start
        
        if event_received:
            logging.info(f"[EVENT-RESULT] stream_stopped_event RECEIVED in {wait_elapsed:.3f}s - SUCCESS")
            logging.info("[LOCAL] ✓ Stream cleanup confirmed via Event - camera freed for high-res capture")
        else:
            logging.warning(f"[EVENT-RESULT] stream_stopped_event TIMEOUT after {wait_elapsed:.3f}s - FAILED")
            logging.warning("[LOCAL] ⚠️ Timeout waiting for stream cleanup - proceeding anyway")
            time.sleep(2.0)  # Fallback safety delay

    try:
        # Step 2: Clear capture complete event before starting capture
        capture_complete_event.clear()
        logging.info(f"[EVENT] capture_complete_event CLEARED at {time.time():.3f}")
        capture_start_time = time.time()
        logging.info(f"[TIMING] Capture cycle START at {capture_start_time:.3f}")
        
        # Step 3: Capture dedicated high-resolution still
        filename = capture_local_image_high_resolution()
        if filename:
            # Step 4: Upload to master
            success = send_local_image(filename)
            if success:
                logging.info("[LOCAL] Still capture protocol completed successfully")
                result = True
            else:
                logging.error("[LOCAL] Failed to upload image to master")
                result = False
        else:
            logging.error("[LOCAL] Failed to capture high-resolution image")
            result = False
    except Exception as e:
        logging.error(f"[LOCAL] Error during still capture protocol: {e}")
        result = False

    # Step 5: Restart video stream if it was running before
    if was_streaming:
        logging.info("[LOCAL] Step 5: Preparing to restart video stream...")
        
        # ARCHITECTURAL FIX: Wait for capture Picamera2 to be fully closed
        # This ensures no instance conflict when new streaming thread creates Picamera2
        wait_start = time.time()
        logging.info(f"[EVENT-WAIT] Waiting for capture_complete_event (timeout=5s) at {wait_start:.3f}...")
        event_received = capture_complete_event.wait(timeout=5.0)  # 5s max wait
        wait_elapsed = time.time() - wait_start
        
        if event_received:
            logging.info(f"[EVENT-RESULT] capture_complete_event RECEIVED in {wait_elapsed:.3f}s - SUCCESS")
            logging.info("[LOCAL] ✓ Capture cleanup confirmed via Event - safe to restart stream")
        else:
            logging.warning(f"[EVENT-RESULT] capture_complete_event TIMEOUT after {wait_elapsed:.3f}s - FAILED")
            logging.warning("[LOCAL] ⚠️ Timeout waiting for capture cleanup - proceeding with caution")
            time.sleep(1.0)  # Extra safety delay
        
        logging.info("[LOCAL] Starting new streaming thread...")
        # BUGFIX: Don't set streaming=True here - let the thread set its own flag
        # This prevents race condition where thread exits immediately due to guard check
        threading.Thread(target=start_local_video_stream, daemon=True).start()
        capture_cycle_time = time.time() - capture_start_time
        logging.info(f"[TIMING] Capture cycle COMPLETE in {capture_cycle_time:.3f}s")
        logging.info("[LOCAL] ✓ Video stream restarted - protocol complete with proper synchronization")
    
    return result

def capture_local_image_high_resolution():
    """FIXED: Capture HIGH RESOLUTION still image (4608, 2592) with working transforms"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/tmp/local_capture_{timestamp}.jpg"
    
    try:
        logging.info("[LOCAL] Starting HIGH-RESOLUTION still capture (4608x2592)...")
        
        picam2 = Picamera2()
        
        # HIGH RESOLUTION configuration (FIXED from working version)
        still_config = picam2.create_still_configuration(
            main={"size": (4608, 2592)}  # ✅ FULL SENSOR RESOLUTION
        )
        
        picam2.configure(still_config)
        picam2.start()
        
        # Allow camera to settle (same as working version)
        time.sleep(1)
        
        # Capture image (RGB format from Picamera2)
        logging.info("[LOCAL] Capturing HIGH-RESOLUTION image...")
        image_rgb = picam2.capture_array()
        
        # Apply unified transforms for still capture (proper BGR format for saving)
        logging.info("[LOCAL] Applying unified still transforms...")
        try:
            from shared.transforms import apply_unified_transforms_for_still
            image_bgr_transformed = apply_unified_transforms_for_still(image_rgb, "rep8")
            logging.info("[LOCAL] ✅ Unified still transforms applied")
        except Exception as e:
            logging.error(f"[LOCAL] Unified still transforms failed: {e}, using fallback")
            # Fallback: apply video transforms then convert to BGR
            image_rgb_transformed = apply_safe_transforms(image_rgb)
            if len(image_rgb_transformed.shape) == 3 and image_rgb_transformed.shape[2] == 3:
                image_bgr_transformed = cv2.cvtColor(image_rgb_transformed, cv2.COLOR_RGB2BGR)
            else:
                image_bgr_transformed = image_rgb_transformed
        
        logging.info("[LOCAL] ✅ Transforms applied - still should match video preview")
        
        # Save image with high quality (FIXED)
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        success = cv2.imwrite(filename, image_bgr_transformed, encode_params)
        
        # Clean up camera
        picam2.stop()
        picam2.close()
        
        # ARCHITECTURAL FIX: Signal that capture Picamera2 is closed
        # This allows streaming to safely restart without instance conflict
        capture_complete_event.set()
        logging.info(f"[EVENT] capture_complete_event SET at {time.time():.3f} - Picamera2 closed")
        logging.info("[LOCAL] ✓ Capture Picamera2 closed - signaled completion")
        
        if success and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            logging.info(f"[LOCAL] ✅ HIGH-RES CAPTURED: {filename} ({file_size} bytes, resolution: 4608x2592)")
            
            # Verify this is actually high resolution
            if file_size > 1000000:  # Should be >1MB for high-res
                logging.info(f"[LOCAL] ✅ Confirmed high-resolution capture (>1MB)")
            else:
                logging.warning(f"[LOCAL] ⚠️ File size seems small for high-res: {file_size} bytes")
            
            return filename
        else:
            logging.error("[LOCAL] ❌ Failed to save captured image")
            return None
            
    except Exception as e:
        logging.error(f"[LOCAL] ❌ Error in high-resolution still capture: {e}")
        logging.error(f"[LOCAL] Exception details: {str(e)}")
        try:
            if 'picam2' in locals():
                picam2.stop()
                picam2.close()
                # ARCHITECTURAL FIX: Signal completion even on error
                capture_complete_event.set()
                logging.info(f"[EVENT] capture_complete_event SET (ERROR PATH) at {time.time():.3f}")
                logging.info("[LOCAL] ✓ Error cleanup complete - signaled completion")
        except:
            # If even cleanup fails, still signal to prevent deadlock
            capture_complete_event.set()
            logging.info(f"[EVENT] capture_complete_event SET (FALLBACK) at {time.time():.3f}")
        return None

def send_local_image(filename):
    """Send local image to master GUI via TCP (same as working version)"""
    for attempt in range(3):
        try:
            logging.info(f"[LOCAL] Uploading image to {MASTER_IP}:{LOCAL_STILL_PORT}... (attempt {attempt + 1}/3)")
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)
                s.connect((MASTER_IP, LOCAL_STILL_PORT))
                
                with open(filename, 'rb') as f:
                    data = f.read()
                    s.sendall(data)
                    logging.info(f"[LOCAL] Uploaded {len(data)} bytes to master")
                    
                try:
                    os.remove(filename)
                    logging.info(f"[LOCAL] Cleaned up temp file: {filename}")
                except:
                    pass
                    
                return True
                    
        except FileNotFoundError:
            logging.error(f"[LOCAL] File not found: {filename}")
            return False
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            logging.error(f"[LOCAL] Connection issue: {e}. Attempt {attempt + 1}/3")
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            logging.error(f"[LOCAL] Error uploading image: {e}")
            return False
    
    logging.error("[LOCAL] Failed to upload image after 3 attempts")
    return False

def handle_local_commands():
    """Enhanced command handler (same as working version)"""
    global streaming, jpeg_quality, camera_settings, video_thread
    
    # Ensure clean initial state
    with streaming_lock:
        streaming = False
        logging.info("[LOCAL] Reset streaming flag to False on startup")
    
    logging.info(f"Starting command handler on port {LOCAL_CONTROL_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(("0.0.0.0", LOCAL_CONTROL_PORT))
        logging.info(f"✓ Command handler listening on port {LOCAL_CONTROL_PORT}")
    except OSError as e:
        logging.error(f"✗ Failed to bind to port {LOCAL_CONTROL_PORT}: {e}")
        return

    command_count = 0
    
    while True:
        try:
            sock.settimeout(5.0)
            data, addr = sock.recvfrom(1024)
            command = data.decode().strip()
            command_count += 1
            
            logging.info(f"[LOCAL] Command #{command_count} from {addr}: {command}")

            if command == "START_STREAM":
                logging.info("Processing START_STREAM command")
                with streaming_lock:
                    current_state = streaming
                if not current_state:
                    logging.info("Starting video thread (streaming was False)")
                    video_thread = threading.Thread(target=start_local_video_stream, daemon=True)
                    video_thread.start()
                else:
                    logging.info(f"Stream already running (streaming = {current_state})")
                    
            elif command == "STOP_STREAM":
                logging.info("Processing STOP_STREAM command")
                stop_local_video_stream()
                
            elif command == "CAPTURE_STILL":
                logging.info("Processing CAPTURE_STILL command - using proper protocol")
                threading.Thread(target=capture_local_still, daemon=True).start()
                
            elif command == "RESTART_STREAM_WITH_SETTINGS":
                restart_local_stream()
                
            elif command == "STATUS":
                status = f"STREAMING:{streaming},HEARTBEAT:{time.time()-last_heartbeat:.1f}s_ago"
                logging.info(f"Status request: {status}")
                
            elif command.startswith("SET_QUALITY_"):
                try:
                    quality = int(command.split('_')[2])
                    if 20 <= quality <= 100:
                        jpeg_quality = quality
                        camera_settings['jpeg_quality'] = quality
                        logging.info(f"JPEG quality set to {quality}")
                except Exception as e:
                    logging.error(f"Invalid quality command: {command}, error: {e}")
            
            # TRANSFORM COMMANDS
            elif command.startswith("SET_CAMERA_CROP_"):
                handle_local_crop_setting(command)
            elif command.startswith("SET_CAMERA_FLIP_"):
                handle_local_flip_setting(command)
            elif command.startswith("SET_CAMERA_GRAYSCALE_"):
                handle_local_grayscale_setting(command)
            elif command.startswith("SET_CAMERA_ROTATION_"):
                handle_local_rotation_setting(command)
            
            # BULK SETTINGS PACKAGE
            elif command.startswith("SET_ALL_SETTINGS_"):
                handle_local_settings_package(command)
            
            # GENERAL CAMERA SETTINGS
            elif command.startswith("SET_CAMERA_"):
                handle_local_camera_setting(command)
            
            # RESET COMMANDS
            elif command == "RESET_CAMERA_DEFAULTS":
                reset_local_to_defaults()
            elif command == "RESET_TO_FACTORY_DEFAULTS":
                factory_reset_local()
            
            # SYSTEM COMMANDS
            elif command in ("SHUTDOWN", "shutdown", "poweroff", "power off", "shut down"):
                logging.info("Shutdown command received. Powering off...")
                stop_local_video_stream()
                os.system("sudo poweroff")
                break
            elif command in ("REBOOT", "reboot"):
                logging.info("Reboot command received. Rebooting...")
                stop_local_video_stream()
                os.system("sudo reboot")
                break
            
            else:
                logging.warning(f"[LOCAL] Unknown command: {command}")
                
        except socket.timeout:
            continue
        except Exception as e:
            logging.error(f"[LOCAL] Error handling command: {e}")

# Settings handling functions (same as working version)
def handle_local_settings_package(command):
    """Handle bulk settings package for local camera"""
    global camera_settings
    try:
        json_part = command[17:]
        new_settings = json.loads(json_part)
        
        for key, value in new_settings.items():
            if key in camera_settings:
                camera_settings[key] = value
                logging.info(f"[LOCAL] Settings package: {key} = {value}")
        
        try:
            from shared.transforms import save_device_settings
            save_device_settings("rep8", camera_settings)
            logging.info(f"[LOCAL] SETTINGS_APPLIED to unified system for rep8")
        except Exception as e:
            logging.error(f"[LOCAL] Failed to save unified settings: {e}")
        
        if streaming:
            logging.info("[LOCAL] Restarting stream for settings package...")
            restart_local_stream()
            logging.info("[LOCAL] STREAM_RESTARTED for rep8")
        
        logging.info(f"[LOCAL] Settings package applied: {len(new_settings)} settings updated")
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling settings package: {e}")

def handle_local_camera_setting(command):
    """Handle standard camera setting commands"""
    global camera_settings
    try:
        parts = command.split('_')
        setting = parts[2].lower()
        value = parts[3]
        
        if setting in ['brightness', 'contrast', 'iso', 'shutter_speed', 'saturation', 'jpeg_quality', 'fps']:
            camera_settings[setting] = int(value)
        elif setting in ['white_balance', 'exposure_mode', 'resolution', 'image_format']:
            camera_settings[setting] = value
        else:
            camera_settings[setting] = value
            
        logging.info(f"[LOCAL] Camera setting updated: {setting} = {value}")
        
        if streaming:
            restart_local_stream()
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling camera setting: {e}")

def handle_local_crop_setting(command):
    """Handle crop setting commands"""
    global camera_settings
    try:
        parts = command.split('_')
        crop_param = parts[3].lower()
        value = parts[4]
        
        if crop_param == 'enabled':
            camera_settings['crop_enabled'] = value.lower() == 'true'
        elif crop_param in ['x', 'y', 'width', 'height']:
            camera_settings[f'crop_{crop_param}'] = int(value)
        
        logging.info(f"[LOCAL] Crop setting updated: crop_{crop_param} = {value}")
        
        if streaming:
            restart_local_stream()
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling crop setting: {e}")

def handle_local_flip_setting(command):
    """FIXED: Handle flip setting without affecting camera brightness"""
    global camera_settings
    try:
        logging.info(f"🔄 [LOCAL] Processing flip command: {command}")
        
        parts = command.split('_')
        flip_direction = parts[3].lower()
        value = parts[4].lower() == 'true'
        
        # FIXED: Only update frame transform settings, never camera controls
        camera_settings[f'flip_{flip_direction}'] = value
        
        logging.info(f"[LOCAL] Flip setting updated: flip_{flip_direction} = {value}")
        logging.info(f"✅ [LOCAL] Updated flip_{flip_direction} = {value} (FRAME ONLY - no camera control changes)")
        
        # Save to settings file
        try:
            from shared.transforms import save_device_settings
            save_device_settings("rep8", camera_settings)
        except Exception as e:
            logging.error(f"[LOCAL] Failed to save flip settings: {e}")
        
        # Restart video stream to apply new transform settings
        if streaming:
            logging.info(f"🔄 [LOCAL] Restarting stream for flip change...")
            restart_local_stream()
        else:
            logging.info(f"⏹️ [LOCAL] Stream not running, settings saved for next start")
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling flip setting: {e}")

def handle_local_grayscale_setting(command):
    """Handle grayscale setting command"""
    global camera_settings
    try:
        logging.info(f"🎨 [LOCAL] Processing grayscale command: {command}")
        
        parts = command.split('_')
        value = parts[3].lower() == 'true'
        
        camera_settings['grayscale'] = value
        
        logging.info(f"[LOCAL] Grayscale setting updated: {value}")
        
        try:
            from shared.transforms import save_device_settings
            save_device_settings("rep8", camera_settings)
        except Exception as e:
            logging.error(f"[LOCAL] Failed to save grayscale settings: {e}")
        
        if streaming:
            logging.info(f"🔄 [LOCAL] Restarting stream for grayscale change...")
            restart_local_stream()
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling grayscale setting: {e}")

def handle_local_rotation_setting(command):
    """Handle rotation setting command"""
    global camera_settings
    try:
        parts = command.split('_')
        rotation = int(parts[3])
        
        if rotation in [0, 90, 180, 270]:
            camera_settings['rotation'] = rotation
            logging.info(f"[LOCAL] Rotation setting updated: {rotation}°")
            
            try:
                from shared.transforms import save_device_settings
                save_device_settings("rep8", camera_settings)
            except Exception as e:
                logging.error(f"[LOCAL] Failed to save rotation settings: {e}")
            
            if streaming:
                restart_local_stream()
        else:
            logging.warning(f"[LOCAL] Invalid rotation value: {rotation}")
        
    except Exception as e:
        logging.error(f"[LOCAL] Error handling rotation setting: {e}")

def reset_local_to_defaults():
    """Reset local camera settings to defaults"""
    global camera_settings
    
    logging.info("[LOCAL] 🔄 Resetting camera to default settings...")
    
    try:
        from shared.transforms import save_device_settings, DEFAULT_SETTINGS
        
        default_settings = DEFAULT_SETTINGS.copy()
        camera_settings = default_settings.copy()
        
        if save_device_settings("rep8", default_settings):
            logging.info(f"[LOCAL] ✅ Default settings saved to rep8_settings.json")
        else:
            logging.error(f"[LOCAL] ❌ Failed to save default settings")
        
        if streaming:
            logging.info("[LOCAL] 🔄 Restarting stream with default settings...")
            restart_local_stream()
        
        logging.info("[LOCAL] ✅ Camera reset to defaults complete")
    except Exception as e:
        logging.error(f"[LOCAL] Error resetting to defaults: {e}")

def restart_local_stream():
    """Restart local video stream with new settings"""
    global streaming, video_thread
    
    logging.info("[LOCAL] 🔄 Restarting video stream with new settings...")
    
    try:
        was_streaming = False
        with streaming_lock:
            was_streaming = streaming
            streaming = False
            
        if was_streaming:
            logging.info("[LOCAL] 🛑 Stopping current stream...")
            
            if video_thread and video_thread.is_alive():
                logging.info("[LOCAL] Waiting for video thread to finish...")
                video_thread.join(timeout=3.0)
                logging.info("[LOCAL] Video thread finished")
        
            time.sleep(0.5)
        
            logging.info("[LOCAL] 🚀 Starting new stream with transforms...")
            video_thread = threading.Thread(target=start_local_video_stream, daemon=True)
            video_thread.start()
            logging.info("[LOCAL] ✅ Video stream restarted successfully")
        else:
            logging.info("[LOCAL] ⏩ Stream wasn't running, no restart needed")
        
    except Exception as e:
        logging.error(f"[LOCAL] ❌ Error during stream restart: {e}")
        with streaming_lock:
            streaming = False

def factory_reset_local():
    """Complete factory reset for local camera"""
    global camera_settings
    
    logging.info("[LOCAL] 🔄 Starting factory reset...")
    
    try:
        from shared.transforms import save_device_settings, DEFAULT_SETTINGS
        
        default_settings = DEFAULT_SETTINGS.copy()
        camera_settings = default_settings.copy()
        
        if save_device_settings("rep8", default_settings):
            logging.info(f"[LOCAL] ✅ Factory defaults saved to rep8_settings.json")
        else:
            logging.error(f"[LOCAL] ❌ Failed to save factory defaults")
        
        if streaming:
            logging.info("[LOCAL] 🔄 Restarting stream after factory reset...")
            restart_local_stream()
            logging.info("[LOCAL] ✅ Stream restarted with factory defaults")
        
        logging.info("[LOCAL] ✅ Factory reset complete")
    except Exception as e:
        logging.error(f"[LOCAL] Error during factory reset: {e}")

def initialize_local_settings():
    """Initialize settings file for rep8 on startup"""
    try:
        device_name = "rep8"
        logging.info(f"[LOCAL] Initializing settings for device: {device_name}")
        
        from shared.transforms import load_device_settings
        settings = load_device_settings(device_name)
        
        logging.info(f"[LOCAL] ✅ Device settings initialized for {device_name}")
        return True
        
    except Exception as e:
        logging.error(f"[LOCAL] Failed to initialize device settings: {e}")
        return False

def main():
    """Main function with enhanced startup"""
    logging.info("[LOCAL] Starting COMPLETE FIXED local camera service...")
    logging.info(f"[LOCAL] ✅ HIGH RESOLUTION: 4608x2592 still captures")
    logging.info(f"[LOCAL] ✅ WORKING TRANSFORMS: Using shared.transforms system")
    logging.info(f"[LOCAL] ✅ CORRECT COLORS: RGB format for GUI")
    logging.info(f"[LOCAL] ✅ PROPER PROTOCOL: Stop→Capture→Upload→Restart")
    logging.info(f"[LOCAL] Configuration: Master={MASTER_IP}")
    logging.info(f"[LOCAL] Control Port={LOCAL_CONTROL_PORT}, Video Port={VIDEO_PORT}, Heartbeat Port={HEARTBEAT_PORT}")
    
    # Initialize device settings on startup
    if not initialize_local_settings():
        logging.error("Failed to initialize local device settings, continuing anyway...")
    
    # Start background services
    logging.info("Starting background services...")
    
    # Start command handler
    cmd_thread = threading.Thread(target=handle_local_commands, daemon=True)
    cmd_thread.start()
    logging.info("✓ Command handler started")
    
    # Start heartbeat
    heartbeat_thread = threading.Thread(target=send_local_heartbeat, daemon=True)
    heartbeat_thread.start()
    logging.info("✓ Heartbeat service started")
    
    time.sleep(2.0)
    
    logging.info("[LOCAL] All services started. Monitoring...")
    logging.info("[LOCAL] ✅ COMPLETE FIX: High-res + working transforms + correct colors")
    logging.info("[LOCAL] Send START_STREAM command to begin video streaming")

    try:
        monitor_count = 0
        while True:
            time.sleep(10)
            monitor_count += 1
            
            status_msg = (f"Monitor #{monitor_count}: "
                         f"Streaming={streaming}, "
                         f"Last heartbeat: {time.time()-last_heartbeat:.1f}s ago")
            logging.info(status_msg)
            
    except KeyboardInterrupt:
        logging.info("[LOCAL] Shutting down local camera service...")
        with streaming_lock:
            if streaming:
                stop_local_video_stream()
    except Exception as e:
        logging.error(f"[LOCAL] Unexpected error in main: {e}")
    finally:
        logging.info("[LOCAL] Local camera service stopped.")

if __name__ == "__main__":
    main()