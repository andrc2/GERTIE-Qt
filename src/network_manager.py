#!/usr/bin/env python3
"""
Network Manager for GERTIE Qt - PySide6 Implementation
Handles UDP communication with Raspberry Pi cameras

Features:
- Non-blocking network operations using QThread
- Command queue for sequential execution
- Status signals for GUI feedback
- Mock mode for MacBook testing
"""

import socket
import time
import logging
from typing import Dict, Optional
from PySide6.QtCore import QThread, Signal, QObject
import json

# Setup logging
logging.basicConfig(level=logging.INFO)


class NetworkCommand:
    """Represents a network command to be sent"""
    
    def __init__(self, ip: str, command: str, port: int = 6000):
        self.ip = ip
        self.command = command
        self.port = port
        self.timestamp = time.time()


class NetworkWorker(QThread):
    """Worker thread for network operations"""
    
    # Signals
    command_sent = Signal(str, str, bool)  # ip, command, success
    error_occurred = Signal(str, str)  # ip, error_message
    
    def __init__(self):
        super().__init__()
        self.command_queue = []
        self.running = True
        self.mock_mode = True  # Default to mock for MacBook testing
        
    def add_command(self, command: NetworkCommand):
        """Add command to queue"""
        self.command_queue.append(command)
        
    def run(self):
        """Main thread loop"""
        logging.info("Network worker thread started")
        
        while self.running:
            if self.command_queue:
                command = self.command_queue.pop(0)
                self._send_command(command)
            else:
                # Sleep briefly to avoid busy-waiting
                self.msleep(10)
                
        logging.info("Network worker thread stopped")
    
    def _send_command(self, command: NetworkCommand):
        """Send a single command"""
        if self.mock_mode:
            # Mock mode - simulate successful send
            logging.info(f"[MOCK] Sending {command.command} to {command.ip}:{command.port}")
            time.sleep(0.01)  # Simulate network delay
            self.command_sent.emit(command.ip, command.command, True)
        else:
            # Real network mode
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2.0)
                sock.sendto(command.command.encode(), (command.ip, command.port))
                sock.close()
                
                logging.info(f"✓ Sent {command.command} to {command.ip}:{command.port}")
                self.command_sent.emit(command.ip, command.command, True)
                
            except Exception as e:
                error_msg = f"Failed to send {command.command} to {command.ip}: {e}"
                logging.error(error_msg)
                self.error_occurred.emit(command.ip, error_msg)
                self.command_sent.emit(command.ip, command.command, False)
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False


class NetworkManager(QObject):
    """Manages network communication with cameras"""
    
    # Signals
    capture_completed = Signal(str)  # ip
    capture_failed = Signal(str, str)  # ip, error
    settings_updated = Signal(str)  # ip
    
    def __init__(self, mock_mode: bool = True):
        super().__init__()
        self.mock_mode = mock_mode
        
        # Create worker thread
        self.worker = NetworkWorker()
        self.worker.mock_mode = mock_mode
        
        # Connect signals
        self.worker.command_sent.connect(self._handle_command_sent)
        self.worker.error_occurred.connect(self._handle_error)
        
        # Start worker
        self.worker.start()
        
        logging.info(f"NetworkManager initialized (mock_mode={mock_mode})")
    
    def send_capture_command(self, ip: str, camera_id: int):
        """Send still capture command to camera"""
        command = NetworkCommand(ip, "CAPTURE_STILL", port=6000)
        self.worker.add_command(command)
        logging.info(f"Queued capture command for camera {camera_id} at {ip}")
    
    def send_settings(self, ip: str, settings: Dict):
        """Send camera settings to device"""
        # Format: SET_ALL_SETTINGS_{json}
        settings_json = json.dumps(settings)
        command_str = f"SET_ALL_SETTINGS_{settings_json}"
        command = NetworkCommand(ip, command_str, port=6000)
        self.worker.add_command(command)
        logging.info(f"Queued settings update for {ip}")
    
    def _handle_command_sent(self, ip: str, command: str, success: bool):
        """Handle command sent confirmation"""
        if success:
            if command == "CAPTURE_STILL":
                self.capture_completed.emit(ip)
            elif command.startswith("SET_ALL_SETTINGS"):
                self.settings_updated.emit(ip)
        else:
            self.capture_failed.emit(ip, "Network send failed")
    
    def _handle_error(self, ip: str, error_msg: str):
        """Handle network error"""
        logging.error(f"Network error for {ip}: {error_msg}")
        self.capture_failed.emit(ip, error_msg)
    
    def set_mock_mode(self, enabled: bool):
        """Enable or disable mock mode"""
        self.mock_mode = enabled
        self.worker.mock_mode = enabled
        logging.info(f"Mock mode {'enabled' if enabled else 'disabled'}")
    
    def shutdown(self):
        """Shutdown network manager"""
        logging.info("Shutting down network manager...")
        self.worker.stop()
        self.worker.wait(1000)  # Wait up to 1 second
        if self.worker.isRunning():
            self.worker.terminate()
        logging.info("Network manager shutdown complete")


# Test code
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    print("NetworkManager Test")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # Create network manager in mock mode
    nm = NetworkManager(mock_mode=True)
    
    # Connect signals
    nm.capture_completed.connect(lambda ip: print(f"✓ Capture completed for {ip}"))
    nm.capture_failed.connect(lambda ip, err: print(f"✗ Capture failed for {ip}: {err}"))
    
    # Send test commands
    print("\nSending test commands...")
    for i in range(3):
        nm.send_capture_command(f"192.168.0.{201+i}", i+1)
    
    # Run for 2 seconds
    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000, app.quit)
    
    app.exec()
    
    # Cleanup
    nm.shutdown()
    
    print("\n✓ NetworkManager test complete")