"""
Lock Screen Application

Phone-style lock screen with:
- Screen timeout and sleep
- 4-digit passcode (optional)
- Notification display
- Wake on any button
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from datetime import datetime
from PIL import Image
import time
import json
import os


class LockScreen(App):
    """Lock screen with passcode and notifications."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='lockscreen',
            name='Lock',
            icon='🔒',
            color='#888888'
        )
        
        # Lock state
        self.is_locked = False
        self.screen_off = False
        self.last_activity = time.time()
        self._saved_brightness = 100  # Store original brightness before sleep
        
        # Passcode
        self.passcode = None  # None = no passcode, otherwise "1234"
        self.entered_code = ""
        self.wrong_attempts = 0
        self.lockout_until = 0
        
        # Settings
        self.timeout_seconds = 30  # Screen timeout
        self.require_passcode = False
        self.background_image_path = None  # Path to background image
        
        # Notifications to display
        self.notifications = []
        
        # Background image cache
        self._bg_image = None
        
        # Load saved settings
        self._load_settings()
    
    def _load_settings(self):
        """Load lock screen settings."""
        config_path = os.path.expanduser('~/.piwrist_lock.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self.passcode = data.get('passcode', None)
                    self.timeout_seconds = data.get('timeout', 30)
                    self.require_passcode = data.get('require_passcode', False)
                    self.background_image_path = data.get('background_image', None)
                    
                    # Don't load image here - defer until display is ready
                    # Image will be loaded in draw() or on_enter()
        except Exception as e:
            print(f"Error loading lock settings: {e}")
    
    def _load_background_image(self):
        """Load background image from file."""
        if not self.background_image_path:
            self._bg_image = None
            return
        
        try:
            # Check if display is available
            if not hasattr(self.ui, 'display') or self.ui.display is None:
                return
            
            # Expand user path and check if file exists
            img_path = os.path.expanduser(self.background_image_path)
            if os.path.exists(img_path):
                img = Image.open(img_path)
                # Resize to fit display (get dimensions from UI)
                try:
                    display_width = self.ui.display.width
                    display_height = self.ui.display.height
                    img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
                    self._bg_image = img
                except AttributeError:
                    # Display not fully initialized yet
                    self._bg_image = None
            else:
                self._bg_image = None
                print(f"Background image not found: {img_path}")
        except Exception as e:
            print(f"Error loading background image: {e}")
            self._bg_image = None
    
    def save_settings(self):
        """Save lock screen settings."""
        config_path = os.path.expanduser('~/.piwrist_lock.json')
        try:
            with open(config_path, 'w') as f:
                json.dump({
                    'passcode': self.passcode,
                    'timeout': self.timeout_seconds,
                    'require_passcode': self.require_passcode,
                    'background_image': self.background_image_path
                }, f)
        except Exception as e:
            print(f"Error saving lock settings: {e}")
    
    def set_background_image(self, image_path: str):
        """Set background image path and load it."""
        self.background_image_path = image_path
        self._load_background_image()
        self.save_settings()
    
    def clear_background_image(self):
        """Remove background image."""
        self.background_image_path = None
        self._bg_image = None
        self.save_settings()
    
    def set_passcode(self, code: str):
        """Set or clear passcode."""
        if code and len(code) == 4 and code.isdigit():
            self.passcode = code
            self.require_passcode = True
        else:
            self.passcode = None
            self.require_passcode = False
        self.save_settings()
    
    def set_timeout(self, seconds: int):
        """Set screen timeout in seconds."""
        self.timeout_seconds = max(10, min(300, seconds))
        self.save_settings()
    
    def add_notification(self, title: str, body: str, icon: str = "📬", source: str = ""):
        """Add a notification to display on lock screen."""
        self.notifications.append({
            'title': title,
            'body': body,
            'icon': icon,
            'source': source,
            'time': datetime.now().strftime('%H:%M')
        })
        # Keep only last 5
        if len(self.notifications) > 5:
            self.notifications.pop(0)
    
    def clear_notifications(self):
        """Clear all notifications."""
        self.notifications = []
    
    def reset_activity(self):
        """Reset activity timer (call on any user input)."""
        # Only reset if we're actually locked
        if not self.is_locked:
            return
        
        self.last_activity = time.time()
        
        # Turn screen back on if off
        if self.screen_off:
            self.screen_off = False
            # Restore saved brightness (default to 100 if not saved)
            if hasattr(self.ui, 'display') and self.ui.display:
                # Ensure we have a valid brightness value
                brightness = self._saved_brightness if self._saved_brightness > 0 else 100
                self.ui.display.set_brightness(brightness)
    
    def lock(self):
        """Lock the device."""
        self.is_locked = True
        self.entered_code = ""
        self.ui.launch_app('lockscreen')
    
    def unlock(self):
        """Unlock the device."""
        self.is_locked = False
        self.entered_code = ""
        self.wrong_attempts = 0
        self.ui.go_home()
    
    def check_timeout(self) -> bool:
        """Check if screen should timeout. Returns True if timed out."""
        if self.timeout_seconds <= 0:
            return False
        
        elapsed = time.time() - self.last_activity
        return elapsed >= self.timeout_seconds
    
    def sleep_screen(self):
        """Turn off screen to save power (but show clock at low brightness)."""
        # Only sleep if we're actually locked
        if not self.is_locked:
            return
        
        # Save current brightness before reducing
        if hasattr(self.ui, 'display') and self.ui.display:
            current_brightness = getattr(self.ui.display, 'brightness', 100)
            self._saved_brightness = current_brightness if current_brightness > 0 else 100
        self.screen_off = True
        # Set to low brightness (15%) instead of 0, so clock is still visible
        if hasattr(self.ui, 'display') and self.ui.display:
            self.ui.display.set_brightness(15)
    
    def on_enter(self):
        """Called when lock screen becomes active."""
        self.entered_code = ""
        self.is_locked = True
        # Reset activity timer
        self.last_activity = time.time()
        # Ensure screen is on
        if self.screen_off:
            self.screen_off = False
            if hasattr(self.ui, 'display') and self.ui.display:
                self.ui.display.set_brightness(self._saved_brightness)
        # Load background image now that display is ready
        if self.background_image_path and not self._bg_image:
            self._load_background_image()
    
    def on_exit(self):
        """Called when leaving lock screen."""
        # Restore brightness when leaving lock screen
        if self.screen_off:
            self.screen_off = False
            if hasattr(self.ui, 'display') and self.ui.display:
                self.ui.display.set_brightness(self._saved_brightness)
    
    def update(self, dt: float):
        """Update lock screen state (called every frame)."""
        # Only check timeout if we're actually locked
        if not self.is_locked:
            return
        
        # Check for timeout and sleep screen if needed
        # Add small buffer (0.1s) to prevent race conditions
        if not self.screen_off and self.timeout_seconds > 0:
            elapsed = time.time() - self.last_activity
            if elapsed >= (self.timeout_seconds - 0.1):
                self.sleep_screen()
    
    def on_key(self, event: KeyEvent) -> bool:
        """Handle key input."""
        # Check if screen was off before resetting activity
        was_screen_off = self.screen_off
        self.reset_activity()
        
        # If screen was off, first press just wakes it (don't process the key)
        if was_screen_off:
            return True
        
        # Check lockout
        if time.time() < self.lockout_until:
            return True
        
        # No passcode - any key unlocks
        if not self.require_passcode or not self.passcode:
            self.unlock()
            return True
        
        # Handle passcode entry
        if event.char and event.char.isdigit():
            if len(self.entered_code) < 4:
                self.entered_code += event.char
                
                # Check if complete
                if len(self.entered_code) == 4:
                    if self.entered_code == self.passcode:
                        self.unlock()
                    else:
                        self.wrong_attempts += 1
                        self.entered_code = ""
                        
                        # Lockout after 3 wrong attempts
                        if self.wrong_attempts >= 3:
                            self.lockout_until = time.time() + 30
                            self.wrong_attempts = 0
            return True
        
        elif event.code == KeyCode.BACKSPACE:
            if self.entered_code:
                self.entered_code = self.entered_code[:-1]
            return True
        
        elif event.code == KeyCode.ESC:
            self.entered_code = ""
            return True
        
        return True
    
    def on_click(self, x: int, y: int) -> bool:
        """Handle click."""
        # Check if screen was off before resetting activity
        was_screen_off = self.screen_off
        self.reset_activity()
        
        # If screen was off, first click just wakes it (don't process the click)
        if was_screen_off:
            return True
        
        if not self.require_passcode or not self.passcode:
            self.unlock()
        
        return True
    
    def draw(self, display: Display):
        """Draw lock screen."""
        if self.screen_off:
            # Show clock at reduced brightness
            display.clear('black')
            
            # Draw clock (large, dim)
            now = datetime.now()
            time_str = now.strftime('%H:%M')
            
            # Clock with shadow for visibility even at low brightness
            display.text(display.width // 2 + 1, display.height // 2 + 1, time_str, '#000000', 64, 'mm')  # Shadow
            display.text(display.width // 2, display.height // 2, time_str, '#666666', 64, 'mm')  # Dim clock (brighter)
            
            display.refresh()
            return
        
        # Lazy-load background image if needed
        if self.background_image_path and not self._bg_image:
            self._load_background_image()
        
        # Background - image or solid color
        if self._bg_image:
            # Create a composite with dark overlay for text readability
            overlay = Image.new('RGBA', (display.width, display.height), (0, 0, 0, 140))
            # Convert background to RGBA if needed
            bg_rgba = self._bg_image.convert('RGBA')
            # Composite overlay onto background
            composite = Image.alpha_composite(bg_rgba, overlay).convert('RGB')
            # Draw the composite image
            display.image(0, 0, composite)
        else:
            # Solid color background
            display.clear('#0a0a1a')
        
        # Clock (large and prominent)
        now = datetime.now()
        time_str = now.strftime('%H:%M')
        date_str = now.strftime('%A, %B %d')
        
        # Time with shadow for visibility over background
        display.text(display.width // 2 + 1, 41, time_str, 'black', 56, 'mm')  # Shadow
        display.text(display.width // 2, 40, time_str, 'white', 56, 'mm')  # Main text
        
        # Date with shadow
        display.text(display.width // 2 + 1, 76, date_str, 'black', 16, 'mm')  # Shadow
        display.text(display.width // 2, 75, date_str, '#cccccc', 16, 'mm')  # Main text
        
        # Notifications
        notif_y = 100
        if self.notifications:
            for i, notif in enumerate(self.notifications[-3:]):  # Show last 3
                self._draw_notification(display, notif, notif_y)
                notif_y += 45
        else:
            display.text(display.width // 2, notif_y + 20, 
                        'No notifications', '#444444', 12, 'mm')
        
        # Lock indicator / passcode entry
        if self.require_passcode and self.passcode:
            self._draw_passcode_entry(display)
        else:
            display.text(display.width // 2, display.height - 40,
                        'Press any key to unlock', '#666666', 12, 'mm')
        
        # Lockout message
        if time.time() < self.lockout_until:
            remaining = int(self.lockout_until - time.time())
            display.rect(20, display.height // 2 - 20, 
                        display.width - 40, 40, fill='#440000')
            display.text(display.width // 2, display.height // 2,
                        f'Locked out: {remaining}s', '#ff4444', 14, 'mm')
    
    def _draw_notification(self, display: Display, notif: dict, y: int):
        """Draw a notification card."""
        x = 10
        w = display.width - 20
        h = 40
        
        # Background
        display.rect(x, y, w, h, fill='#1a1a2e', color='#2a2a3e')
        
        # Icon
        display.text(x + 15, y + h // 2, notif['icon'], 'white', 16, 'mm')
        
        # Title and time
        display.text(x + 35, y + 10, notif['title'][:20], 'white', 12)
        display.text(w - 5, y + 10, notif['time'], '#666666', 10, 'rt')
        
        # Body preview
        body = notif['body'][:30] + '...' if len(notif['body']) > 30 else notif['body']
        display.text(x + 35, y + 26, body, '#888888', 10)
    
    def _draw_passcode_entry(self, display: Display):
        """Draw passcode entry area."""
        y = display.height - 60
        
        # Dots for entered digits
        dot_spacing = 25
        start_x = display.width // 2 - (dot_spacing * 1.5)
        
        for i in range(4):
            x = int(start_x + i * dot_spacing)
            if i < len(self.entered_code):
                # Filled dot
                display.circle(x, y, 8, fill='white')
            else:
                # Empty dot
                display.circle(x, y, 8, color='#666666', width=2)
        
        # Instructions
        if self.wrong_attempts > 0:
            display.text(display.width // 2, y + 25,
                        f'Wrong code ({3 - self.wrong_attempts} tries left)', 
                        '#ff4444', 11, 'mm')
        else:
            display.text(display.width // 2, y + 25,
                        'Enter passcode', '#666666', 11, 'mm')

