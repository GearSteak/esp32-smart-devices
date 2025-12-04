"""
Shadowdark Light Tracker
Tracks torch/lantern/spell light duration with alarms.
"""

import time
import threading
from typing import Optional
from src.ui.display import Display
from src.input.cardkb import KeyEvent, KeyCode


class LightSource:
    """Represents an active light source."""
    
    def __init__(self, name: str, duration_minutes: int, icon: str = "🔥"):
        self.name = name
        self.icon = icon
        self.total_seconds = duration_minutes * 60
        self.remaining_seconds = self.total_seconds
        self.active = False
        self.start_time: Optional[float] = None
        self.paused_at: Optional[float] = None
    
    def start(self):
        """Start or resume the timer."""
        if self.paused_at:
            # Resume from pause
            elapsed_while_paused = time.time() - self.paused_at
            self.start_time += elapsed_while_paused
            self.paused_at = None
        elif not self.active:
            self.start_time = time.time()
        self.active = True
    
    def pause(self):
        """Pause the timer."""
        if self.active and not self.paused_at:
            self.paused_at = time.time()
    
    def toggle(self):
        """Toggle between running and paused."""
        if self.paused_at:
            self.start()
        elif self.active:
            self.pause()
        else:
            self.start()
    
    def add_minute(self):
        """Add 1 minute to remaining time."""
        self.remaining_seconds = min(self.total_seconds, self.remaining_seconds + 60)
        if self.start_time and self.active:
            self.start_time += 60
    
    def subtract_minute(self):
        """Remove 1 minute from remaining time."""
        self.remaining_seconds = max(0, self.remaining_seconds - 60)
        if self.start_time and self.active:
            self.start_time -= 60
    
    def get_remaining(self) -> int:
        """Get remaining seconds."""
        if not self.active or not self.start_time:
            return self.remaining_seconds
        
        if self.paused_at:
            elapsed = self.paused_at - self.start_time
        else:
            elapsed = time.time() - self.start_time
        
        remaining = self.total_seconds - int(elapsed)
        self.remaining_seconds = max(0, remaining)
        return self.remaining_seconds
    
    def is_expired(self) -> bool:
        """Check if light has expired."""
        return self.get_remaining() <= 0
    
    def reset(self):
        """Reset to full duration."""
        self.remaining_seconds = self.total_seconds
        self.start_time = None
        self.paused_at = None
        self.active = False


# Predefined light sources for Shadowdark
LIGHT_PRESETS = [
    ("Torch", 60, "🔥"),
    ("Lantern", 240, "🏮"),  # 4 hours per oil flask
    ("Light Spell", 60, "✨"),
    ("Candle", 60, "🕯️"),
    ("Custom", 30, "💡"),
]


class LightTrackerApp:
    """
    Shadowdark Light Tracker
    
    Tracks multiple light sources with real-time countdowns.
    Alarms at 5 minutes and 0 minutes remaining.
    """
    
    def __init__(self, ui):
        self.ui = ui
        self.active_lights: list[LightSource] = []
        self.selected_index = 0
        self.mode = 'main'  # main, add_light, editing
        self.preset_index = 0
        self.custom_minutes = 60
        
        # Alarm state
        self.alarm_triggered_5min: set[int] = set()
        self.alarm_triggered_0min: set[int] = set()
        self.showing_alarm = False
        self.alarm_message = ""
        self.alarm_time = 0
        
        # Flashing state for alarms
        self.flash_state = False
        self.last_flash = 0
    
    def on_enter(self):
        """Called when app becomes active."""
        self.mode = 'main'
        self.selected_index = 0
    
    def on_exit(self):
        """Called when leaving app."""
        pass
    
    def handle_input(self, event: KeyEvent) -> bool:
        """Handle input events."""
        if event.type != 'press':
            return False
        
        # Dismiss alarm with any key
        if self.showing_alarm:
            self.showing_alarm = False
            return True
        
        if self.mode == 'main':
            return self._handle_main_input(event)
        elif self.mode == 'add_light':
            return self._handle_add_light_input(event)
        elif self.mode == 'editing':
            return self._handle_editing_input(event)
        
        return False
    
    def _handle_main_input(self, event: KeyEvent) -> bool:
        """Handle main screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.ui.go_back()
            return True
        
        if not self.active_lights:
            # No lights, only allow adding
            if event.code == KeyCode.ENTER or event.char == 'a':
                self.mode = 'add_light'
                self.preset_index = 0
                return True
            return False
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.active_lights) - 1, self.selected_index + 1)
            return True
        elif event.code == KeyCode.ENTER:
            # Toggle pause/resume
            if self.active_lights:
                self.active_lights[self.selected_index].toggle()
            return True
        elif event.code == KeyCode.LEFT:
            # Subtract 1 minute
            if self.active_lights:
                self.active_lights[self.selected_index].subtract_minute()
            return True
        elif event.code == KeyCode.RIGHT:
            # Add 1 minute
            if self.active_lights:
                self.active_lights[self.selected_index].add_minute()
            return True
        elif event.char == 'a' or event.char == 'A':
            # Add new light
            self.mode = 'add_light'
            self.preset_index = 0
            return True
        elif event.char == 'r' or event.char == 'R':
            # Reset selected light
            if self.active_lights:
                self.active_lights[self.selected_index].reset()
            return True
        elif event.char == 'd' or event.char == 'D' or event.code == KeyCode.DELETE:
            # Delete selected light
            if self.active_lights:
                # Clear alarm tracking for this index
                if self.selected_index in self.alarm_triggered_5min:
                    self.alarm_triggered_5min.discard(self.selected_index)
                if self.selected_index in self.alarm_triggered_0min:
                    self.alarm_triggered_0min.discard(self.selected_index)
                
                del self.active_lights[self.selected_index]
                self.selected_index = min(self.selected_index, len(self.active_lights) - 1)
                self.selected_index = max(0, self.selected_index)
            return True
        
        return False
    
    def _handle_add_light_input(self, event: KeyEvent) -> bool:
        """Handle add light screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'main'
            return True
        
        if event.code == KeyCode.UP:
            self.preset_index = max(0, self.preset_index - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.preset_index = min(len(LIGHT_PRESETS) - 1, self.preset_index + 1)
            return True
        elif event.code == KeyCode.LEFT and self.preset_index == len(LIGHT_PRESETS) - 1:
            # Adjust custom minutes
            self.custom_minutes = max(1, self.custom_minutes - 5)
            return True
        elif event.code == KeyCode.RIGHT and self.preset_index == len(LIGHT_PRESETS) - 1:
            # Adjust custom minutes
            self.custom_minutes = min(480, self.custom_minutes + 5)
            return True
        elif event.code == KeyCode.ENTER:
            # Add selected light
            name, duration, icon = LIGHT_PRESETS[self.preset_index]
            if self.preset_index == len(LIGHT_PRESETS) - 1:
                duration = self.custom_minutes
            
            new_light = LightSource(name, duration, icon)
            new_light.start()
            self.active_lights.append(new_light)
            self.selected_index = len(self.active_lights) - 1
            self.mode = 'main'
            return True
        
        return False
    
    def _handle_editing_input(self, event: KeyEvent) -> bool:
        """Handle editing mode input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'main'
            return True
        return False
    
    def _check_alarms(self):
        """Check for alarm conditions."""
        for i, light in enumerate(self.active_lights):
            remaining = light.get_remaining()
            
            # 5 minute warning
            if remaining <= 300 and remaining > 0 and light.active:
                if i not in self.alarm_triggered_5min:
                    self.alarm_triggered_5min.add(i)
                    self.showing_alarm = True
                    self.alarm_message = f"⚠️ {light.name} - 5 MINUTES!"
                    self.alarm_time = time.time()
            
            # Expired alarm
            if remaining <= 0 and light.active:
                if i not in self.alarm_triggered_0min:
                    self.alarm_triggered_0min.add(i)
                    self.showing_alarm = True
                    self.alarm_message = f"🔴 {light.name} EXPIRED!"
                    self.alarm_time = time.time()
                    light.active = False
    
    def draw(self, display: Display):
        """Draw the light tracker interface."""
        self._check_alarms()
        
        # Update flash state
        if time.time() - self.last_flash > 0.5:
            self.flash_state = not self.flash_state
            self.last_flash = time.time()
        
        # Alarm overlay
        if self.showing_alarm:
            self._draw_alarm(display)
            return
        
        if self.mode == 'add_light':
            self._draw_add_light(display)
        else:
            self._draw_main(display)
    
    def _draw_main(self, display: Display):
        """Draw main light tracker screen."""
        # Header
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a0505')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🔥 LIGHT TRACKER", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        if not self.active_lights:
            # No lights
            display.text(display.width // 2, display.height // 2 - 20,
                        "No active lights", '#666666', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        "Press A to add light", '#888888', 12, 'mm')
            return
        
        # Draw light sources
        item_height = 50
        for i, light in enumerate(self.active_lights):
            y = content_y + i * item_height
            
            if y + item_height > display.height - 30:
                break
            
            remaining = light.get_remaining()
            minutes = remaining // 60
            seconds = remaining % 60
            
            # Selection highlight
            selected = (i == self.selected_index)
            if selected:
                display.rect(0, y, display.width, item_height - 2, fill='#2a1a1a')
            
            # Determine color based on time remaining
            if remaining <= 0:
                time_color = '#666666'
                status = "EXPIRED"
            elif remaining <= 60:  # 1 minute - critical
                time_color = '#ff0000' if self.flash_state else '#aa0000'
                status = "CRITICAL"
            elif remaining <= 300:  # 5 minutes - warning
                time_color = '#ff6600'
                status = "LOW"
            else:
                time_color = '#00ff00'
                status = "OK"
            
            # Pause indicator
            if light.paused_at:
                status = "PAUSED"
                time_color = '#ffff00'
            elif not light.active:
                status = "STOPPED"
                time_color = '#666666'
            
            # Icon and name
            display.text(10, y + 12, light.icon, 'white', 18)
            display.text(40, y + 10, light.name, 'white' if selected else '#cccccc', 14)
            display.text(40, y + 28, status, time_color, 10)
            
            # Time display
            time_str = f"{minutes:02d}:{seconds:02d}"
            display.text(display.width - 15, y + 20, time_str, time_color, 24, 'rm')
        
        # Controls help
        help_y = display.height - 22
        display.rect(0, help_y - 3, display.width, 25, fill='#0a0a0a')
        display.text(5, help_y + 7, "←-1m →+1m ⏎Pause A:Add D:Del", '#666666', 10, 'lm')
    
    def _draw_add_light(self, display: Display):
        """Draw add light menu."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a0505')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "ADD LIGHT SOURCE", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        for i, (name, duration, icon) in enumerate(LIGHT_PRESETS):
            y = content_y + i * 35
            selected = (i == self.preset_index)
            
            if selected:
                display.rect(0, y - 2, display.width, 32, fill='#2a1a1a')
            
            # For custom, show adjustable duration
            if i == len(LIGHT_PRESETS) - 1:
                duration = self.custom_minutes
            
            display.text(15, y + 10, icon, 'white', 16)
            display.text(45, y + 10, name, 'white' if selected else '#888888', 14)
            
            hours = duration // 60
            mins = duration % 60
            if hours > 0:
                dur_str = f"{hours}h {mins}m" if mins else f"{hours}h"
            else:
                dur_str = f"{mins}m"
            
            display.text(display.width - 15, y + 10, dur_str, '#ffaa00' if selected else '#666666', 14, 'rm')
            
            # Show arrows for custom
            if i == len(LIGHT_PRESETS) - 1 and selected:
                display.text(display.width - 70, y + 10, "← →", '#888888', 10, 'rm')
        
        # Help
        display.text(display.width // 2, display.height - 15,
                    "⏎ Select  ESC Back", '#666666', 10, 'mm')
    
    def _draw_alarm(self, display: Display):
        """Draw alarm overlay."""
        # Flashing background
        bg_color = '#ff0000' if self.flash_state else '#880000'
        display.rect(0, 0, display.width, display.height, fill=bg_color)
        
        # Alarm message
        display.text(display.width // 2, display.height // 2 - 10,
                    self.alarm_message, 'white', 18, 'mm')
        
        display.text(display.width // 2, display.height // 2 + 30,
                    "Press any key", 'white', 12, 'mm')

