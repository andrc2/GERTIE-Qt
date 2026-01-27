"""
Audio feedback module for GERTIE Qt
Provides shutter sound on capture events (non-blocking)
"""

import subprocess
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioFeedback:
    """Manages audio feedback for capture events"""
    
    def __init__(self):
        self.enabled = True  # Default enabled
        self.volume = 100    # 0-100
        self.sound_file = self._find_sound_file()
        logger.info(f"[AUDIO] Initialized - sound: {self.sound_file}, enabled: {self.enabled}")
        
    def _find_sound_file(self):
        """Find appropriate sound file for platform"""
        # Check for custom shutter.wav in project
        project_sounds = [
            Path(__file__).parent / "shutter.wav",
            Path(__file__).parent.parent / "shutter.wav",
            Path(__file__).parent / "assets" / "shutter.wav",
        ]
        
        for sound_path in project_sounds:
            if sound_path.exists():
                logger.info(f"[AUDIO] Found project sound: {sound_path}")
                return str(sound_path)
        
        # Platform-specific fallbacks
        if sys.platform == 'darwin':
            # macOS system sounds
            macos_sounds = [
                '/System/Library/Sounds/Pop.aiff',
                '/System/Library/Sounds/Tink.aiff', 
                '/System/Library/Sounds/Glass.aiff',
                '/System/Library/Sounds/Purr.aiff',
            ]
            for sound in macos_sounds:
                if os.path.exists(sound):
                    return sound
                    
        elif sys.platform.startswith('linux'):
            # Linux/Raspberry Pi - check for common sounds
            linux_sounds = [
                '/usr/share/sounds/freedesktop/stereo/camera-shutter.oga',
                '/usr/share/sounds/freedesktop/stereo/complete.oga',
                '/usr/share/sounds/sound-icons/prompt.wav',
            ]
            for sound in linux_sounds:
                if os.path.exists(sound):
                    return sound
        
        # No sound file found - will use system beep
        return None
    
    def play_capture_sound(self, count: int = 1):
        """Play capture sound effect (non-blocking)
        
        Args:
            count: Number of rapid shutter sounds to play (for burst capture)
        """
        if not self.enabled:
            return
        
        # Play multiple sounds in rapid succession for burst capture
        for i in range(count):
            self._play_single_sound()
    
    def _play_single_sound(self):
        """Play a single shutter sound (internal)"""
        try:
            if self.sound_file and os.path.exists(self.sound_file):
                # Play sound file
                if sys.platform == 'darwin':
                    # macOS: use afplay
                    cmd = ['afplay', self.sound_file]
                elif sys.platform.startswith('linux'):
                    # Linux/Raspberry Pi: try aplay first, then paplay
                    if self.sound_file.endswith('.oga'):
                        cmd = ['paplay', self.sound_file]
                    else:
                        cmd = ['aplay', '-q', self.sound_file]
                else:
                    logger.debug(f"[AUDIO] Unsupported platform: {sys.platform}")
                    return
                    
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.debug(f"[AUDIO] Playing: {self.sound_file}")
                
            else:
                # Fallback: system beep
                if sys.platform.startswith('linux'):
                    # Try speaker-test for a quick beep
                    subprocess.Popen(
                        ['speaker-test', '-t', 'sine', '-f', '800', '-l', '1'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                logger.debug("[AUDIO] Using system beep fallback")
                               
        except Exception as e:
            # Silently fail - audio is non-critical
            logger.debug(f"[AUDIO] Playback failed: {e}")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable audio feedback"""
        self.enabled = enabled
        logger.info(f"[AUDIO] {'Enabled' if enabled else 'Disabled'}")
    
    def set_volume(self, volume: int):
        """Set volume level (0-100) - for future use"""
        self.volume = max(0, min(100, volume))
        logger.info(f"[AUDIO] Volume set to {self.volume}%")


# Global singleton instance
_audio_instance = None


def get_audio() -> AudioFeedback:
    """Get or create global audio feedback instance"""
    global _audio_instance
    if _audio_instance is None:
        _audio_instance = AudioFeedback()
    return _audio_instance


def play_capture_sound(count: int = 1):
    """Convenience function - play capture shutter sound(s)
    
    Args:
        count: Number of rapid shutter sounds (default 1, use 8 for Capture All)
    """
    get_audio().play_capture_sound(count)


def set_audio_enabled(enabled: bool):
    """Convenience function - enable/disable audio"""
    get_audio().set_enabled(enabled)
