#!/usr/bin/env python3
"""
GERTIE Qt - Network Manager (Expanded)
Complete UDP communication with Raspberry Pi cameras

Features:
- Non-blocking network operations using QThread
- Command queue for sequential execution
- All commands from Tkinter version
- Comprehensive logging
- Mock mode for MacBook testing
- Real network mode for Pi deployment

Author: Andrew Crane / Claude GERTIE Session
Date: 2025-11-28
"""

import socket
import time
import logging
import json
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QThread, Signal, QObject, QMutex, QMutexLocker

# Import config
from config import (
    SLAVES, MASTER_IP, get_slave_ports, get_camera_id_from_ip,
    is_local_camera, STILL_PORT, HEARTBEAT_PORT
)

# Setup module logging
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class CommandType(Enum):
    """Types of network commands"""
    CAPTURE = "capture"
    VIDEO_CONTROL = "video_control"
    SETTINGS = "settings"
    TRANSFORM = "transform"
    SYSTEM = "system"
    HEARTBEAT = "heartbeat"


class CommandPriority(Enum):
    """Command priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class NetworkCommand:
    """Represents a network command to be sent"""
    ip: str
    command: str
    port: int = 6000
    command_type: CommandType = CommandType.CAPTURE
    priority: CommandPriority = CommandPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    camera_id: int = 0
    callback: Optional[Callable] = None
    retries: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.camera_id == 0:
            self.camera_id = get_camera_id_from_ip(self.ip)


# =============================================================================
# NETWORK WORKER THREAD
# =============================================================================

class NetworkWorker(QThread):
    """Worker thread for network operations with comprehensive logging"""
    
    # Signals
    command_sent = Signal(str, str, bool, str)  # ip, command, success, details
    error_occurred = Signal(str, str, str)  # ip, command, error_message
    command_queued = Signal(str, str, int)  # ip, command, queue_position
    
    def __init__(self):
        super().__init__()
        self.command_queue: List[NetworkCommand] = []
        self.running = True
        self.mock_mode = True  # Default to mock for MacBook testing
        self.mutex = QMutex()
        
        # Statistics
        self.stats = {
            'commands_sent': 0,
            'commands_failed': 0,
            'bytes_sent': 0,
            'start_time': time.time()
        }
        
        logger.info("[NETWORK] NetworkWorker initialized")
        
    def add_command(self, command: NetworkCommand) -> int:
        """Add command to queue, returns queue position"""
        with QMutexLocker(self.mutex):
            # Insert based on priority
            insert_pos = len(self.command_queue)
            for i, queued_cmd in enumerate(self.command_queue):
                if command.priority.value > queued_cmd.priority.value:
                    insert_pos = i
                    break
            
            self.command_queue.insert(insert_pos, command)
            queue_pos = insert_pos + 1
            
        logger.debug(f"[NETWORK] Queued: {command.command[:50]}... to {command.ip} "
                    f"(pos={queue_pos}, priority={command.priority.name})")
        self.command_queued.emit(command.ip, command.command[:50], queue_pos)
        return queue_pos
        
    def run(self):
        """Main thread loop"""
        logger.info("[NETWORK] Worker thread started")
        
        while self.running:
            command = None
            with QMutexLocker(self.mutex):
                if self.command_queue:
                    command = self.command_queue.pop(0)
            
            if command:
                self._send_command(command)
            else:
                # Sleep briefly to avoid busy-waiting
                self.msleep(10)
                
        logger.info("[NETWORK] Worker thread stopped")
        self._log_stats()
    
    def _send_command(self, command: NetworkCommand):
        """Send a single command with logging"""
        start_time = time.time()
        
        if self.mock_mode:
            self._send_mock(command, start_time)
        else:
            self._send_real(command, start_time)
    
    def _send_mock(self, command: NetworkCommand, start_time: float):
        """Mock send - simulate successful transmission"""
        # Simulate network delay
        time.sleep(0.01)
        
        elapsed = (time.time() - start_time) * 1000
        self.stats['commands_sent'] += 1
        self.stats['bytes_sent'] += len(command.command)
        
        details = f"MOCK send completed in {elapsed:.1f}ms"
        logger.info(f"[NETWORK] [MOCK] ✓ Sent to {command.ip}:{command.port} - "
                   f"{command.command[:50]}... ({elapsed:.1f}ms)")
        
        self.command_sent.emit(command.ip, command.command, True, details)
        
        # Execute callback if provided
        if command.callback:
            try:
                command.callback(True, command)
            except Exception as e:
                logger.error(f"[NETWORK] Callback error: {e}")
    
    def _send_real(self, command: NetworkCommand, start_time: float):
        """Real network send via UDP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            
            data = command.command.encode('utf-8')
            sock.sendto(data, (command.ip, command.port))
            sock.close()
            
            elapsed = (time.time() - start_time) * 1000
            self.stats['commands_sent'] += 1
            self.stats['bytes_sent'] += len(data)
            
            details = f"UDP send completed in {elapsed:.1f}ms, {len(data)} bytes"
            logger.info(f"[NETWORK] ✓ Sent to {command.ip}:{command.port} - "
                       f"{command.command[:50]}... ({elapsed:.1f}ms, {len(data)}B)")
            
            self.command_sent.emit(command.ip, command.command, True, details)
            
            # Execute callback if provided
            if command.callback:
                try:
                    command.callback(True, command)
                except Exception as e:
                    logger.error(f"[NETWORK] Callback error: {e}")
                
        except socket.timeout:
            self._handle_send_error(command, "Socket timeout", start_time)
        except socket.error as e:
            self._handle_send_error(command, f"Socket error: {e}", start_time)
        except Exception as e:
            self._handle_send_error(command, f"Unexpected error: {e}", start_time)
    
    def _handle_send_error(self, command: NetworkCommand, error_msg: str, start_time: float):
        """Handle send failure with retry logic"""
        elapsed = (time.time() - start_time) * 1000
        
        if command.retries < command.max_retries:
            command.retries += 1
            logger.warning(f"[NETWORK] ⚠ Send failed to {command.ip}:{command.port} - "
                          f"{error_msg} - Retry {command.retries}/{command.max_retries}")
            # Re-queue with same priority
            self.add_command(command)
        else:
            self.stats['commands_failed'] += 1
            logger.error(f"[NETWORK] ✗ Send FAILED to {command.ip}:{command.port} - "
                        f"{command.command[:50]}... - {error_msg} ({elapsed:.1f}ms)")
            
            self.error_occurred.emit(command.ip, command.command, error_msg)
            self.command_sent.emit(command.ip, command.command, False, error_msg)
            
            # Execute callback with failure
            if command.callback:
                try:
                    command.callback(False, command)
                except Exception as e:
                    logger.error(f"[NETWORK] Callback error: {e}")
    
    def _log_stats(self):
        """Log session statistics"""
        elapsed = time.time() - self.stats['start_time']
        logger.info(f"[NETWORK] Session stats: "
                   f"sent={self.stats['commands_sent']}, "
                   f"failed={self.stats['commands_failed']}, "
                   f"bytes={self.stats['bytes_sent']}, "
                   f"duration={elapsed:.1f}s")
    
    def stop(self):
        """Stop the worker thread"""
        logger.info("[NETWORK] Stopping worker thread...")
        self.running = False
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        with QMutexLocker(self.mutex):
            return len(self.command_queue)
    
    def clear_queue(self):
        """Clear all pending commands"""
        with QMutexLocker(self.mutex):
            count = len(self.command_queue)
            self.command_queue.clear()
        logger.info(f"[NETWORK] Cleared {count} commands from queue")


# =============================================================================
# HEARTBEAT MONITOR
# =============================================================================

class HeartbeatMonitor(QThread):
    """Monitor heartbeat signals from cameras"""
    
    # Signals
    camera_online = Signal(str, int)  # ip, camera_id
    camera_offline = Signal(str, int)  # ip, camera_id
    heartbeat_received = Signal(str, int)  # ip, camera_id
    status_update = Signal(dict)  # {camera_id: online_status}
    
    def __init__(self, timeout_seconds: float = 5.0):
        super().__init__()
        self.running = True
        self.mock_mode = True
        self.timeout_seconds = timeout_seconds
        self.mutex = QMutex()
        
        # Track last heartbeat time for each camera
        self.last_heartbeat: Dict[str, float] = {}
        self.camera_status: Dict[int, bool] = {}  # camera_id -> online
        
        # Initialize all cameras as offline
        for name, config in SLAVES.items():
            camera_id = get_camera_id_from_ip(config["ip"])
            self.camera_status[camera_id] = False
            self.last_heartbeat[config["ip"]] = 0
        
        logger.info(f"[HEARTBEAT] Monitor initialized (timeout={timeout_seconds}s)")
    
    def run(self):
        """Main heartbeat monitoring loop"""
        logger.info("[HEARTBEAT] Monitor thread started")
        
        if self.mock_mode:
            self._run_mock_mode()
        else:
            self._run_real_mode()
        
        logger.info("[HEARTBEAT] Monitor thread stopped")
    
    def _run_mock_mode(self):
        """Mock mode - simulate all cameras online"""
        logger.info("[HEARTBEAT] Running in MOCK mode - all cameras simulated online")
        
        # Simulate initial connection
        self.msleep(500)
        
        for name, config in SLAVES.items():
            ip = config["ip"]
            camera_id = get_camera_id_from_ip(ip)
            
            with QMutexLocker(self.mutex):
                self.last_heartbeat[ip] = time.time()
                self.camera_status[camera_id] = True
            
            logger.info(f"[HEARTBEAT] [MOCK] Camera {camera_id} ({name}) online")
            self.camera_online.emit(ip, camera_id)
            self.heartbeat_received.emit(ip, camera_id)
        
        self.status_update.emit(self.camera_status.copy())
        
        # Keep running to maintain status
        while self.running:
            self.msleep(1000)
            
            # Simulate periodic heartbeats
            current_time = time.time()
            for name, config in SLAVES.items():
                ip = config["ip"]
                with QMutexLocker(self.mutex):
                    self.last_heartbeat[ip] = current_time
    
    def _run_real_mode(self):
        """Real mode - listen for actual UDP heartbeats"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", HEARTBEAT_PORT))
            sock.settimeout(1.0)  # 1 second timeout for checking stop condition
            
            logger.info(f"[HEARTBEAT] Listening on port {HEARTBEAT_PORT}")
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode().strip()
                    
                    if message == "HEARTBEAT":
                        ip = addr[0]
                        camera_id = get_camera_id_from_ip(ip)
                        
                        with QMutexLocker(self.mutex):
                            was_offline = not self.camera_status.get(camera_id, False)
                            self.last_heartbeat[ip] = time.time()
                            self.camera_status[camera_id] = True
                        
                        if was_offline:
                            logger.info(f"[HEARTBEAT] Camera {camera_id} ({ip}) came ONLINE")
                            self.camera_online.emit(ip, camera_id)
                        
                        self.heartbeat_received.emit(ip, camera_id)
                        logger.debug(f"[HEARTBEAT] Received from camera {camera_id} ({ip})")
                        
                except socket.timeout:
                    pass  # Expected, check for timeouts
                except Exception as e:
                    logger.error(f"[HEARTBEAT] Receive error: {e}")
                
                # Check for camera timeouts
                self._check_timeouts()
            
            sock.close()
            
        except OSError as e:
            logger.error(f"[HEARTBEAT] Failed to bind to port {HEARTBEAT_PORT}: {e}")
    
    def _check_timeouts(self):
        """Check for cameras that have gone offline"""
        current_time = time.time()
        
        with QMutexLocker(self.mutex):
            for ip, last_time in self.last_heartbeat.items():
                camera_id = get_camera_id_from_ip(ip)
                was_online = self.camera_status.get(camera_id, False)
                
                if last_time > 0 and (current_time - last_time) > self.timeout_seconds:
                    if was_online:
                        self.camera_status[camera_id] = False
                        logger.warning(f"[HEARTBEAT] Camera {camera_id} ({ip}) went OFFLINE "
                                      f"(no heartbeat for {self.timeout_seconds}s)")
                        self.camera_offline.emit(ip, camera_id)
    
    def get_camera_status(self, camera_id: int) -> bool:
        """Get online status for a camera"""
        with QMutexLocker(self.mutex):
            return self.camera_status.get(camera_id, False)
    
    def get_all_status(self) -> dict:
        """Get status of all cameras"""
        with QMutexLocker(self.mutex):
            return self.camera_status.copy()
    
    def get_online_cameras(self) -> List[int]:
        """Get list of online camera IDs"""
        with QMutexLocker(self.mutex):
            return [cid for cid, online in self.camera_status.items() if online]
    
    def stop(self):
        """Stop the monitor thread"""
        logger.info("[HEARTBEAT] Stopping monitor...")
        self.running = False


# =============================================================================
# MAIN NETWORK MANAGER
# =============================================================================

class NetworkManager(QObject):
    """
    Complete network communication manager for GERTIE Qt.
    
    Provides all commands from Tkinter version:
    - Still capture (CAPTURE_STILL)
    - Video control (START_STREAM, STOP_STREAM, RESTART_STREAM_WITH_SETTINGS)
    - Settings (SET_ALL_SETTINGS_, individual SET_CAMERA_* commands)
    - Transforms (SET_CAMERA_CROP_*, FLIP_*, GRAYSCALE_*, ROTATION_*)
    - System (SHUTDOWN, REBOOT, RESET_TO_FACTORY_DEFAULTS)
    """
    
    # Signals
    capture_completed = Signal(str, int)  # ip, camera_id
    capture_failed = Signal(str, int, str)  # ip, camera_id, error
    settings_updated = Signal(str, int)  # ip, camera_id
    video_started = Signal(str, int)  # ip, camera_id
    video_stopped = Signal(str, int)  # ip, camera_id
    command_sent = Signal(str, str, bool)  # ip, command_type, success
    camera_online = Signal(int)  # camera_id
    camera_offline = Signal(int)  # camera_id
    mode_changed = Signal(bool)  # mock_mode
    
    def __init__(self, mock_mode: bool = True):
        super().__init__()
        self.mock_mode = mock_mode
        
        # Create worker thread
        self.worker = NetworkWorker()
        self.worker.mock_mode = mock_mode
        
        # Create heartbeat monitor
        self.heartbeat_monitor = HeartbeatMonitor(timeout_seconds=5.0)
        self.heartbeat_monitor.mock_mode = mock_mode
        
        # Connect worker signals
        self.worker.command_sent.connect(self._handle_command_sent)
        self.worker.error_occurred.connect(self._handle_error)
        
        # Connect heartbeat signals
        self.heartbeat_monitor.camera_online.connect(
            lambda ip, cid: self.camera_online.emit(cid))
        self.heartbeat_monitor.camera_offline.connect(
            lambda ip, cid: self.camera_offline.emit(cid))
        
        # Start threads
        self.worker.start()
        self.heartbeat_monitor.start()
        
        logger.info(f"[MANAGER] NetworkManager initialized (mock_mode={mock_mode})")
    
    # =========================================================================
    # MODE CONTROL
    # =========================================================================
    
    def set_mock_mode(self, enabled: bool):
        """Enable or disable mock mode"""
        if self.mock_mode != enabled:
            self.mock_mode = enabled
            self.worker.mock_mode = enabled
            self.heartbeat_monitor.mock_mode = enabled
            
            mode_str = "MOCK" if enabled else "REAL NETWORK"
            logger.info(f"[MANAGER] Mode changed to {mode_str}")
            self.mode_changed.emit(enabled)
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode"""
        return self.mock_mode
    
    # =========================================================================
    # CAPTURE COMMANDS
    # =========================================================================
    
    def send_capture_command(self, ip: str, camera_id: int = 0):
        """Send still capture command to camera"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="CAPTURE_STILL",
            port=ports['still'],
            command_type=CommandType.CAPTURE,
            priority=CommandPriority.HIGH,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued CAPTURE_STILL for camera {camera_id} ({ip})")
    
    def send_capture_all(self):
        """Send capture command to all cameras"""
        logger.info("[MANAGER] Sending CAPTURE_STILL to ALL cameras")
        for name, config in SLAVES.items():
            ip = config["ip"]
            camera_id = get_camera_id_from_ip(ip)
            self.send_capture_command(ip, camera_id)
    
    # =========================================================================
    # VIDEO STREAM COMMANDS
    # =========================================================================
    
    def send_start_stream(self, ip: str, camera_id: int = 0):
        """Send start stream command"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="START_STREAM",
            port=ports['video_control'],
            command_type=CommandType.VIDEO_CONTROL,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued START_STREAM for camera {camera_id} ({ip})")
    
    def send_stop_stream(self, ip: str, camera_id: int = 0):
        """Send stop stream command"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="STOP_STREAM",
            port=ports['video_control'],
            command_type=CommandType.VIDEO_CONTROL,
            priority=CommandPriority.HIGH,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued STOP_STREAM for camera {camera_id} ({ip})")
    
    def send_restart_stream(self, ip: str, camera_id: int = 0):
        """Send restart stream with settings command"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="RESTART_STREAM_WITH_SETTINGS",
            port=ports['video_control'],
            command_type=CommandType.VIDEO_CONTROL,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued RESTART_STREAM for camera {camera_id} ({ip})")
    
    def send_start_all_streams(self):
        """Start video streams on all cameras"""
        logger.info("[MANAGER] Starting streams on ALL cameras")
        for name, config in SLAVES.items():
            self.send_start_stream(config["ip"])
    
    def send_stop_all_streams(self):
        """Stop video streams on all cameras"""
        logger.info("[MANAGER] Stopping streams on ALL cameras")
        for name, config in SLAVES.items():
            self.send_stop_stream(config["ip"])
    

    # =========================================================================
    # SETTINGS COMMANDS
    # =========================================================================
    
    def send_settings(self, ip: str, settings: Dict, camera_id: int = 0):
        """Send camera settings as bulk package (preferred method)"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        settings_json = json.dumps(settings)
        command_str = f"SET_ALL_SETTINGS_{settings_json}"
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.SETTINGS,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued SET_ALL_SETTINGS for camera {camera_id} "
                   f"({len(settings)} settings)")
    
    def send_individual_setting(self, ip: str, setting_name: str, value, camera_id: int = 0):
        """Send individual camera setting"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        command_str = f"SET_CAMERA_{setting_name.upper()}_{value}"
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.SETTINGS,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued {command_str} for camera {camera_id}")
    
    def send_quality(self, ip: str, quality: int, camera_id: int = 0):
        """Send JPEG quality setting (20-100)"""
        quality = max(20, min(100, quality))
        self.send_individual_setting(ip, "QUALITY", quality, camera_id)
    
    def send_brightness(self, ip: str, brightness: int, camera_id: int = 0):
        """Send brightness setting (-50 to +50, 0 = neutral)"""
        brightness = max(-50, min(50, brightness))
        self.send_individual_setting(ip, "BRIGHTNESS", brightness, camera_id)
    
    def send_contrast(self, ip: str, contrast: int, camera_id: int = 0):
        """Send contrast setting (0-100, 50 = neutral)"""
        contrast = max(0, min(100, contrast))
        self.send_individual_setting(ip, "CONTRAST", contrast, camera_id)
    
    def send_saturation(self, ip: str, saturation: int, camera_id: int = 0):
        """Send saturation setting (0-100, 50 = neutral)"""
        saturation = max(0, min(100, saturation))
        self.send_individual_setting(ip, "SATURATION", saturation, camera_id)
    
    def send_iso(self, ip: str, iso: int, camera_id: int = 0):
        """Send ISO setting (100-6400)"""
        iso = max(100, min(6400, iso))
        self.send_individual_setting(ip, "ISO", iso, camera_id)
    
    # =========================================================================
    # TRANSFORM COMMANDS
    # =========================================================================
    
    def send_flip_horizontal(self, ip: str, enabled: bool, camera_id: int = 0):
        """Send horizontal flip setting"""
        value = "TRUE" if enabled else "FALSE"
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        command_str = f"SET_CAMERA_FLIP_HORIZONTAL_{value}"
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.TRANSFORM,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued flip_horizontal={enabled} for camera {camera_id}")
    
    def send_flip_vertical(self, ip: str, enabled: bool, camera_id: int = 0):
        """Send vertical flip setting"""
        value = "TRUE" if enabled else "FALSE"
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        command_str = f"SET_CAMERA_FLIP_VERTICAL_{value}"
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.TRANSFORM,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued flip_vertical={enabled} for camera {camera_id}")
    
    def send_rotation(self, ip: str, degrees: int, camera_id: int = 0):
        """Send rotation setting (0, 90, 180, 270)"""
        if degrees not in [0, 90, 180, 270]:
            logger.warning(f"[MANAGER] Invalid rotation {degrees}, using 0")
            degrees = 0
        
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        command_str = f"SET_CAMERA_ROTATION_{degrees}"
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.TRANSFORM,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued rotation={degrees} for camera {camera_id}")
    
    def send_grayscale(self, ip: str, enabled: bool, camera_id: int = 0):
        """Send grayscale setting"""
        value = "TRUE" if enabled else "FALSE"
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        command_str = f"SET_CAMERA_GRAYSCALE_{value}"
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command=command_str,
            port=ports['control'],
            command_type=CommandType.TRANSFORM,
            priority=CommandPriority.NORMAL,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.info(f"[MANAGER] Queued grayscale={enabled} for camera {camera_id}")
    
    def send_crop(self, ip: str, x: int, y: int, width: int, height: int, 
                  enabled: bool = True, camera_id: int = 0):
        """Send crop settings"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        # Send as bulk settings for atomicity
        crop_settings = {
            'crop_enabled': enabled,
            'crop_x': x,
            'crop_y': y,
            'crop_width': width,
            'crop_height': height
        }
        self.send_settings(ip, crop_settings, camera_id)
        logger.info(f"[MANAGER] Queued crop settings for camera {camera_id}")
    

    # =========================================================================
    # SYSTEM COMMANDS
    # =========================================================================
    
    def send_factory_reset(self, ip: str, camera_id: int = 0):
        """Send factory reset command"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="RESET_TO_FACTORY_DEFAULTS",
            port=ports['control'],
            command_type=CommandType.SYSTEM,
            priority=CommandPriority.HIGH,
            camera_id=camera_id
        )
        self.worker.add_command(command)
        logger.warning(f"[MANAGER] Queued FACTORY_RESET for camera {camera_id}")
    
    def send_shutdown(self, ip: str, camera_id: int = 0):
        """Send shutdown command to camera Pi"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="SHUTDOWN",
            port=ports['control'],
            command_type=CommandType.SYSTEM,
            priority=CommandPriority.CRITICAL,
            camera_id=camera_id,
            max_retries=1  # Don't retry shutdown
        )
        self.worker.add_command(command)
        logger.warning(f"[MANAGER] Queued SHUTDOWN for camera {camera_id} ({ip})")
    
    def send_reboot(self, ip: str, camera_id: int = 0):
        """Send reboot command to camera Pi"""
        if camera_id == 0:
            camera_id = get_camera_id_from_ip(ip)
        
        ports = get_slave_ports(ip)
        command = NetworkCommand(
            ip=ip,
            command="REBOOT",
            port=ports['control'],
            command_type=CommandType.SYSTEM,
            priority=CommandPriority.CRITICAL,
            camera_id=camera_id,
            max_retries=1  # Don't retry reboot
        )
        self.worker.add_command(command)
        logger.warning(f"[MANAGER] Queued REBOOT for camera {camera_id} ({ip})")
    
    def send_shutdown_all(self):
        """Shutdown all camera Pis"""
        logger.warning("[MANAGER] Sending SHUTDOWN to ALL cameras")
        for name, config in SLAVES.items():
            if not config.get("local", False):  # Don't shutdown local
                self.send_shutdown(config["ip"])
    
    def send_reboot_all(self):
        """Reboot all camera Pis"""
        logger.warning("[MANAGER] Sending REBOOT to ALL cameras")
        for name, config in SLAVES.items():
            if not config.get("local", False):  # Don't reboot local
                self.send_reboot(config["ip"])
    
    # =========================================================================
    # INTERNAL HANDLERS
    # =========================================================================
    
    def _handle_command_sent(self, ip: str, command: str, success: bool, details: str):
        """Handle command sent confirmation"""
        camera_id = get_camera_id_from_ip(ip)
        
        if success:
            if command == "CAPTURE_STILL":
                self.capture_completed.emit(ip, camera_id)
            elif command.startswith("SET_ALL_SETTINGS"):
                self.settings_updated.emit(ip, camera_id)
            elif command == "START_STREAM":
                self.video_started.emit(ip, camera_id)
            elif command == "STOP_STREAM":
                self.video_stopped.emit(ip, camera_id)
            
            # Generic signal
            cmd_type = command.split('_')[0] if '_' in command else command
            self.command_sent.emit(ip, cmd_type, True)
        else:
            if command == "CAPTURE_STILL":
                self.capture_failed.emit(ip, camera_id, details)
            
            cmd_type = command.split('_')[0] if '_' in command else command
            self.command_sent.emit(ip, cmd_type, False)
    
    def _handle_error(self, ip: str, command: str, error_msg: str):
        """Handle network error"""
        camera_id = get_camera_id_from_ip(ip)
        logger.error(f"[MANAGER] Network error for camera {camera_id} ({ip}): {error_msg}")
        
        if "CAPTURE" in command:
            self.capture_failed.emit(ip, camera_id, error_msg)
    
    # =========================================================================
    # STATUS AND UTILITY
    # =========================================================================
    
    def get_queue_size(self) -> int:
        """Get number of pending commands"""
        return self.worker.get_queue_size()
    
    def clear_queue(self):
        """Clear all pending commands"""
        self.worker.clear_queue()
    
    def get_camera_status(self, camera_id: int) -> bool:
        """Get online status of a camera"""
        return self.heartbeat_monitor.get_camera_status(camera_id)
    
    def get_all_camera_status(self) -> dict:
        """Get online status of all cameras"""
        return self.heartbeat_monitor.get_all_status()
    
    def get_online_cameras(self) -> List[int]:
        """Get list of online camera IDs"""
        return self.heartbeat_monitor.get_online_cameras()
    
    def get_stats(self) -> dict:
        """Get network statistics"""
        return self.worker.stats.copy()
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    
    def shutdown(self):
        """Shutdown network manager and all threads"""
        logger.info("[MANAGER] Shutting down NetworkManager...")
        
        # Stop heartbeat monitor
        self.heartbeat_monitor.stop()
        self.heartbeat_monitor.wait(2000)
        if self.heartbeat_monitor.isRunning():
            logger.warning("[MANAGER] Force terminating heartbeat monitor")
            self.heartbeat_monitor.terminate()
        
        # Stop worker
        self.worker.stop()
        self.worker.wait(2000)
        if self.worker.isRunning():
            logger.warning("[MANAGER] Force terminating network worker")
            self.worker.terminate()
        
        logger.info("[MANAGER] NetworkManager shutdown complete")


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    print("=" * 70)
    print("GERTIE Qt - NetworkManager Comprehensive Test")
    print("=" * 70)
    
    app = QApplication(sys.argv)
    
    # Create network manager in mock mode
    nm = NetworkManager(mock_mode=True)
    
    # Track test results
    results = {
        'captures': 0,
        'settings': 0,
        'video_cmds': 0,
        'errors': 0
    }
    
    # Connect signals
    def on_capture_complete(ip, cid):
        results['captures'] += 1
        print(f"  ✓ Capture completed: camera {cid} ({ip})")
    
    def on_capture_failed(ip, cid, err):
        results['errors'] += 1
        print(f"  ✗ Capture failed: camera {cid} - {err}")
    
    def on_settings_updated(ip, cid):
        results['settings'] += 1
        print(f"  ✓ Settings updated: camera {cid}")
    
    def on_video_started(ip, cid):
        results['video_cmds'] += 1
        print(f"  ✓ Video started: camera {cid}")
    
    def on_video_stopped(ip, cid):
        results['video_cmds'] += 1
        print(f"  ✓ Video stopped: camera {cid}")
    
    def on_camera_online(cid):
        print(f"  📡 Camera {cid} online")
    
    nm.capture_completed.connect(on_capture_complete)
    nm.capture_failed.connect(on_capture_failed)
    nm.settings_updated.connect(on_settings_updated)
    nm.video_started.connect(on_video_started)
    nm.video_stopped.connect(on_video_stopped)
    nm.camera_online.connect(on_camera_online)
    
    print("\n--- Test 1: Capture Commands ---")
    
    # Test single capture
    nm.send_capture_command("192.168.0.201", 1)
    nm.send_capture_command("192.168.0.202", 2)
    
    print("\n--- Test 2: Video Stream Commands ---")
    
    nm.send_start_stream("192.168.0.203", 3)
    nm.send_stop_stream("192.168.0.203", 3)
    nm.send_restart_stream("192.168.0.204", 4)
    
    print("\n--- Test 3: Bulk Settings ---")
    
    test_settings = {
        'brightness': 10,
        'contrast': 55,
        'iso': 200,
        'flip_horizontal': True
    }
    nm.send_settings("192.168.0.205", test_settings, 5)
    
    print("\n--- Test 4: Individual Settings ---")
    
    nm.send_brightness("192.168.0.206", 15, 6)
    nm.send_contrast("192.168.0.206", 60, 6)
    nm.send_quality("192.168.0.206", 90, 6)
    
    print("\n--- Test 5: Transform Commands ---")
    
    nm.send_flip_horizontal("192.168.0.207", True, 7)
    nm.send_flip_vertical("192.168.0.207", False, 7)
    nm.send_rotation("192.168.0.207", 90, 7)
    nm.send_grayscale("192.168.0.207", True, 7)
    
    print("\n--- Test 6: Local Camera (rep8) ---")
    
    nm.send_capture_command("127.0.0.1", 8)
    nm.send_start_stream("127.0.0.1", 8)
    
    print("\n--- Test 7: System Commands ---")
    
    nm.send_factory_reset("192.168.0.201", 1)
    # Note: Not testing shutdown/reboot in automated test
    
    print("\n--- Test 8: Batch Operations ---")
    
    nm.send_capture_all()
    
    # Run event loop for 3 seconds to process all commands
    def finish_test():
        print("\n" + "=" * 70)
        print("Test Results:")
        print("=" * 70)
        print(f"  Captures completed: {results['captures']}")
        print(f"  Settings updated: {results['settings']}")
        print(f"  Video commands: {results['video_cmds']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Queue size: {nm.get_queue_size()}")
        print(f"  Online cameras: {nm.get_online_cameras()}")
        
        stats = nm.get_stats()
        print(f"\nNetwork Stats:")
        print(f"  Commands sent: {stats['commands_sent']}")
        print(f"  Commands failed: {stats['commands_failed']}")
        print(f"  Bytes sent: {stats['bytes_sent']}")
        
        print("\n" + "=" * 70)
        
        # Cleanup
        nm.shutdown()
        app.quit()
    
    QTimer.singleShot(3000, finish_test)
    
    print("\nProcessing commands (3 second test)...")
    app.exec()
    
    print("\n✓ NetworkManager comprehensive test complete")
