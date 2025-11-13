#!/usr/bin/env python3
"""
Mock Camera Data Generator for GERTIE Qt Development
Simulates 8 Raspberry Pi camera feeds for MacBook testing

Features:
- Multiple test pattern generators (color bars, grid, noise, gradient)
- Configurable resolution (640x480 default to match video preview)
- Frame rate control
- Camera ID overlays
- Timestamp overlays
- Simulated network latency
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
from typing import Tuple, Optional
import random


class MockCamera:
    """Simulates a single Raspberry Pi camera feed"""
    
    def __init__(
        self,
        camera_id: int,
        resolution: Tuple[int, int] = (640, 480),
        fps: int = 30,
        pattern: str = "color_bars"
    ):
        """
        Initialize mock camera
        
        Args:
            camera_id: Camera identifier (1-8)
            resolution: Frame resolution (width, height)
            fps: Target frames per second
            pattern: Test pattern type (color_bars, grid, noise, gradient, checkerboard)
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.fps = fps
        self.pattern = pattern
        self.frame_count = 0
        self.start_time = time.time()
        
        # Calculate frame interval
        self.frame_interval = 1.0 / fps
        
        # Pattern-specific state
        self.hue_offset = (camera_id - 1) * (360 / 8)  # Unique color per camera
        
    def generate_frame(self) -> Image.Image:
        """Generate a single frame based on selected pattern"""
        
        if self.pattern == "color_bars":
            frame = self._generate_color_bars()
        elif self.pattern == "grid":
            frame = self._generate_grid()
        elif self.pattern == "noise":
            frame = self._generate_noise()
        elif self.pattern == "gradient":
            frame = self._generate_gradient()
        elif self.pattern == "checkerboard":
            frame = self._generate_checkerboard()
        else:
            frame = self._generate_color_bars()  # Default
        
        # Add overlays
        frame = self._add_camera_id(frame)
        frame = self._add_timestamp(frame)
        frame = self._add_frame_count(frame)
        
        self.frame_count += 1
        return frame
    
    def _generate_color_bars(self) -> Image.Image:
        """Generate SMPTE color bars pattern"""
        width, height = self.resolution
        img = Image.new('RGB', self.resolution)
        draw = ImageDraw.Draw(img)
        
        # SMPTE color bars (7 colors)
        colors = [
            (192, 192, 192),  # White/Gray
            (192, 192, 0),    # Yellow
            (0, 192, 192),    # Cyan
            (0, 192, 0),      # Green
            (192, 0, 192),    # Magenta
            (192, 0, 0),      # Red
            (0, 0, 192),      # Blue
        ]
        
        # Adjust colors based on camera ID for distinction
        hue_shift = self.camera_id * 10
        colors = [(min(255, r + hue_shift), g, b) for r, g, b in colors]
        
        bar_width = width // len(colors)
        for i, color in enumerate(colors):
            x1 = i * bar_width
            x2 = x1 + bar_width if i < len(colors) - 1 else width
            draw.rectangle([x1, 0, x2, height], fill=color)
        
        return img
    
    def _generate_grid(self) -> Image.Image:
        """Generate grid pattern with animated position"""
        width, height = self.resolution
        img = Image.new('RGB', self.resolution, color=(40, 40, 40))
        draw = ImageDraw.Draw(img)
        
        # Grid parameters
        grid_size = 40
        offset = (self.frame_count * 2) % grid_size  # Animate grid movement
        
        # Camera-specific color
        hue = (self.hue_offset + self.frame_count) % 360
        color = self._hue_to_rgb(hue)
        
        # Draw vertical lines
        for x in range(-grid_size + offset, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=color, width=2)
        
        # Draw horizontal lines
        for y in range(-grid_size + offset, height, grid_size):
            draw.line([(0, y), (width, y)], fill=color, width=2)
        
        return img
    
    def _generate_noise(self) -> Image.Image:
        """Generate random noise pattern (like static)"""
        width, height = self.resolution
        
        # Generate random noise
        noise_array = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        
        # Add camera-specific color tint
        tint = self._hue_to_rgb(self.hue_offset)
        noise_array = np.clip(noise_array * 0.7 + np.array(tint) * 0.3, 0, 255).astype(np.uint8)
        
        img = Image.fromarray(noise_array)
        return img
    
    def _generate_gradient(self) -> Image.Image:
        """Generate animated gradient pattern"""
        width, height = self.resolution
        
        # Create gradient array
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Animated angle based on frame count
        angle = (self.frame_count * 2) % 360
        hue_start = (self.hue_offset + angle) % 360
        
        for y in range(height):
            progress = y / height
            hue = (hue_start + progress * 120) % 360
            color = self._hue_to_rgb(hue)
            gradient[y, :] = color
        
        img = Image.fromarray(gradient)
        return img
    
    def _generate_checkerboard(self) -> Image.Image:
        """Generate animated checkerboard pattern"""
        width, height = self.resolution
        img = Image.new('RGB', self.resolution)
        draw = ImageDraw.Draw(img)
        
        square_size = 40
        offset = (self.frame_count * 3) % (square_size * 2)
        
        color1 = self._hue_to_rgb(self.hue_offset)
        color2 = self._hue_to_rgb((self.hue_offset + 180) % 360)
        
        for y in range(0, height, square_size):
            for x in range(0, width, square_size):
                if ((x + y + offset) // square_size) % 2 == 0:
                    draw.rectangle([x, y, x + square_size, y + square_size], fill=color1)
                else:
                    draw.rectangle([x, y, x + square_size, y + square_size], fill=color2)
        
        return img
    
    def _add_camera_id(self, img: Image.Image) -> Image.Image:
        """Add camera ID overlay to frame"""
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except:
            font = ImageFont.load_default()
        
        # Camera ID text
        text = f"REP{self.camera_id}"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position in top-left
        x = 10
        y = 10
        
        # Draw background rectangle
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)
        )
        
        # Draw text
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        return img
    
    def _add_timestamp(self, img: Image.Image) -> Image.Image:
        """Add timestamp overlay to frame"""
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font = ImageFont.load_default()
        
        # Current timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), timestamp, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position in top-right
        x = img.width - text_width - 20
        y = 10
        
        # Draw background
        padding = 5
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)
        )
        
        # Draw text
        draw.text((x, y), timestamp, fill=(0, 255, 0), font=font)
        
        return img
    
    def _add_frame_count(self, img: Image.Image) -> Image.Image:
        """Add frame counter overlay"""
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        
        # Frame info
        elapsed = time.time() - self.start_time
        actual_fps = self.frame_count / elapsed if elapsed > 0 else 0
        text = f"Frame: {self.frame_count} | FPS: {actual_fps:.1f}"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position in bottom-left
        x = 10
        y = img.height - text_height - 20
        
        # Draw background
        padding = 5
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)
        )
        
        # Draw text
        draw.text((x, y), text, fill=(255, 255, 0), font=font)
        
        return img
    
    def _hue_to_rgb(self, hue: float) -> Tuple[int, int, int]:
        """Convert HSV hue (0-360) to RGB tuple with full saturation and value"""
        # Normalize hue to 0-1
        h = (hue % 360) / 360.0
        
        # HSV to RGB conversion (S=1, V=1)
        i = int(h * 6)
        f = h * 6 - i
        
        q = 1.0 - f
        t = f
        
        i = i % 6
        
        if i == 0:
            r, g, b = 1, t, 0
        elif i == 1:
            r, g, b = q, 1, 0
        elif i == 2:
            r, g, b = 0, 1, t
        elif i == 3:
            r, g, b = 0, q, 1
        elif i == 4:
            r, g, b = t, 0, 1
        else:
            r, g, b = 1, 0, q
        
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def get_fps(self) -> float:
        """Get actual FPS for this camera"""
        elapsed = time.time() - self.start_time
        return self.frame_count / elapsed if elapsed > 0 else 0.0
    
    def reset_stats(self):
        """Reset frame counter and timing stats"""
        self.frame_count = 0
        self.start_time = time.time()


class MockCameraSystem:
    """Manages 8 mock cameras simulating GERTIE hardware"""
    
    def __init__(
        self,
        resolution: Tuple[int, int] = (640, 480),
        fps: int = 30,
        patterns: Optional[list] = None
    ):
        """
        Initialize 8-camera mock system
        
        Args:
            resolution: Frame resolution for all cameras
            fps: Target frames per second
            patterns: List of pattern types for each camera (defaults to variety)
        """
        if patterns is None:
            # Default: cycle through different patterns
            patterns = ["color_bars", "grid", "noise", "gradient", 
                       "checkerboard", "color_bars", "grid", "gradient"]
        
        if len(patterns) < 8:
            # Pad with color_bars if needed
            patterns = patterns + ["color_bars"] * (8 - len(patterns))
        
        self.cameras = [
            MockCamera(i + 1, resolution, fps, patterns[i])
            for i in range(8)
        ]
        
        self.resolution = resolution
        self.fps = fps
    
    def generate_all_frames(self) -> list:
        """Generate frames from all 8 cameras simultaneously"""
        return [camera.generate_frame() for camera in self.cameras]
    
    def get_system_fps(self) -> float:
        """Get average FPS across all cameras"""
        fps_values = [camera.get_fps() for camera in self.cameras]
        return sum(fps_values) / len(fps_values) if fps_values else 0.0
    
    def reset_all_stats(self):
        """Reset stats for all cameras"""
        for camera in self.cameras:
            camera.reset_stats()


# Test code
if __name__ == "__main__":
    print("Mock Camera System Test")
    print("=" * 60)
    
    # Create system
    system = MockCameraSystem(resolution=(640, 480), fps=30)
    
    # Generate 10 frames
    print("Generating 10 test frames from all 8 cameras...")
    start = time.time()
    
    for i in range(10):
        frames = system.generate_all_frames()
        print(f"Frame {i+1}: Generated {len(frames)} frames")
        time.sleep(1/30)  # Simulate 30 FPS
    
    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.2f}s")
    print(f"System FPS: {system.get_system_fps():.1f}")
    print("\n✓ Mock camera system working!")
