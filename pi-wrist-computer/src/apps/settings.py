"""
Settings Application

System configuration for:
- WiFi
- Display brightness
- Theme
- About device
"""

from ..ui.framework import App, AppInfo, Rect, ListBox, Label
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import subprocess
import os


class SettingsApp(App):
    """Settings application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='settings',
            name='Settings',
            icon='⚙',
            color='#888888'
        )
        
        self.menu_items = [
            ('wifi', 'WiFi', '📶'),
            ('bluetooth', 'Bluetooth', '🔵'),
            ('display', 'Display', '☀'),
            ('lock', 'Lock Screen', '🔒'),
            ('sound', 'Sound', '🔊'),
            ('gps', 'GPS', '📍'),
            ('apps', 'Apps', '📱'),
            ('about', 'About', 'ℹ'),
        ]
        
        # Passcode entry state
        self.entering_passcode = False
        self.new_passcode = ""
        
        self.selected_index = 0
        self.in_submenu = False
        self.submenu_items = []
        self.submenu_index = 0
        self.scroll_offset = 0  # For main menu
        self.submenu_scroll = 0  # For submenu
    
    def on_enter(self):
        """Setup settings menu."""
        self.selected_index = 0
        self.in_submenu = False
    
    def on_exit(self):
        pass
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.in_submenu:
            return self._handle_submenu_key(event)
        
        # Calculate visible items
        item_height = 35
        available_height = self.ui.display.height - self.ui.STATUS_BAR_HEIGHT - 30
        max_visible = available_height // item_height
        
        if event.code == KeyCode.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
                # Scroll up if needed
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_index < len(self.menu_items) - 1:
                self.selected_index += 1
                # Scroll down if needed
                if self.selected_index >= self.scroll_offset + max_visible:
                    self.scroll_offset = self.selected_index - max_visible + 1
            return True
        elif event.code == KeyCode.ENTER:
            self._open_submenu(self.menu_items[self.selected_index][0])
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.ui.go_home()
            return True
        
        return False
    
    def _handle_submenu_key(self, event: KeyEvent) -> bool:
        # Handle passcode entry mode
        if self.entering_passcode:
            if event.char and event.char.isdigit() and len(self.new_passcode) < 4:
                self.new_passcode += event.char
                if len(self.new_passcode) == 4:
                    # Save passcode
                    lock_app = self.ui.apps.get('lockscreen')
                    if lock_app:
                        lock_app.set_passcode(self.new_passcode)
                        self.submenu_items[1] = ('lock_passcode', 'Passcode: Set', None)
                    self.entering_passcode = False
                    self.new_passcode = ""
                return True
            elif event.code == KeyCode.BACKSPACE:
                if self.new_passcode:
                    self.new_passcode = self.new_passcode[:-1]
                return True
            elif event.code == KeyCode.ESC:
                self.entering_passcode = False
                self.new_passcode = ""
                return True
            return True
        
        # Calculate visible items for submenu
        item_height = 35
        available_height = self.ui.display.height - self.ui.STATUS_BAR_HEIGHT - 30
        max_visible = available_height // item_height
        
        if event.code == KeyCode.UP:
            if self.submenu_index > 0:
                self.submenu_index -= 1
                # Scroll up if needed
                if self.submenu_index < self.submenu_scroll:
                    self.submenu_scroll = self.submenu_index
            return True
        elif event.code == KeyCode.DOWN:
            if self.submenu_index < len(self.submenu_items) - 1:
                self.submenu_index += 1
                # Scroll down if needed
                if self.submenu_index >= self.submenu_scroll + max_visible:
                    self.submenu_scroll = self.submenu_index - max_visible + 1
            return True
        elif event.code == KeyCode.ENTER:
            self._handle_submenu_action()
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            # Go back to settings menu, not main menu
            self.in_submenu = False
            return True
        elif event.code == KeyCode.LEFT or event.code == KeyCode.RIGHT:
            # Handle value adjustment
            self._adjust_value(event.code == KeyCode.RIGHT)
            return True
        
        return False
    
    def _open_submenu(self, menu_id: str):
        """Open a submenu."""
        self.in_submenu = True
        self.submenu_index = 0
        self.submenu_scroll = 0  # Reset scroll when opening submenu
        
        if menu_id == 'display':
            brightness = self.ui.display.brightness
            self.submenu_items = [
                ('brightness', f'Brightness: {brightness}%', brightness),
                ('rotation', f'Rotation: {self.ui.display.rotation}°', None),
                ('theme', 'Theme: Dark', None),
            ]
        elif menu_id == 'wifi':
            self.submenu_items = [
                ('wifi_status', 'Status: Checking...', None),
                ('wifi_ssid', 'Network: --', None),
                ('wifi_config', 'Configure WiFi...', None),
            ]
            self._check_wifi_status()
        elif menu_id == 'bluetooth':
            self.submenu_items = [
                ('bt_status', 'Status: Checking...', None),
                ('bt_paired', 'Paired devices: 0', None),
                ('bt_scan', 'Scan for devices...', None),
            ]
        elif menu_id == 'gps':
            self.submenu_items = [
                ('gps_status', 'Status: Checking...', None),
                ('gps_fix', 'Fix: --', None),
                ('gps_coords', 'Position: --', None),
            ]
        elif menu_id == 'lock':
            # Get lock screen app
            lock_app = self.ui.apps.get('lockscreen')
            if lock_app:
                timeout = lock_app.timeout_seconds
                has_passcode = 'Set' if lock_app.passcode else 'None'
            else:
                timeout = 30
                has_passcode = 'None'
            
            bg_status = 'Set' if lock_app and lock_app.background_image_path else 'None'
            self.submenu_items = [
                ('lock_timeout', f'Timeout: {timeout}s', timeout),
                ('lock_passcode', f'Passcode: {has_passcode}', None),
                ('lock_set_passcode', 'Set New Passcode...', None),
                ('lock_clear_passcode', 'Clear Passcode', None),
                ('lock_bg_image', f'Background: {bg_status}', None),
                ('lock_set_bg', 'Set Background Image...', None),
                ('lock_clear_bg', 'Clear Background', None),
                ('lock_now', 'Lock Now', None),
            ]
        elif menu_id == 'about':
            self.submenu_items = [
                ('about_name', 'Pi Wrist Computer', None),
                ('about_version', 'Version: 1.0.0', None),
                ('about_hostname', f'Hostname: {self._get_hostname()}', None),
                ('about_ip', f'IP: {self._get_ip()}', None),
            ]
        else:
            self.submenu_items = [('none', 'Coming soon...', None)]
    
    def _check_wifi_status(self):
        """Check WiFi status."""
        try:
            result = subprocess.run(['iwgetid', '-r'], 
                                   capture_output=True, text=True, timeout=2)
            ssid = result.stdout.strip()
            if ssid:
                self.submenu_items[0] = ('wifi_status', 'Status: Connected', None)
                self.submenu_items[1] = ('wifi_ssid', f'Network: {ssid}', None)
                self.ui.wifi_connected = True
            else:
                self.submenu_items[0] = ('wifi_status', 'Status: Disconnected', None)
                self.ui.wifi_connected = False
        except Exception:
            self.submenu_items[0] = ('wifi_status', 'Status: Error', None)
    
    def _get_hostname(self) -> str:
        try:
            return subprocess.run(['hostname'], capture_output=True, 
                                 text=True, timeout=2).stdout.strip()
        except Exception:
            return 'unknown'
    
    def _get_ip(self) -> str:
        try:
            result = subprocess.run(
                ['hostname', '-I'], capture_output=True, text=True, timeout=2)
            ips = result.stdout.strip().split()
            return ips[0] if ips else 'No IP'
        except Exception:
            return 'unknown'
    
    def _adjust_value(self, increase: bool):
        """Adjust a value in submenu."""
        if not self.submenu_items:
            return
        
        item_id, text, value = self.submenu_items[self.submenu_index]
        
        if item_id == 'brightness' and value is not None:
            new_val = min(100, value + 10) if increase else max(10, value - 10)
            self.ui.display.set_brightness(new_val)
            self.submenu_items[self.submenu_index] = (
                'brightness', f'Brightness: {new_val}%', new_val
            )
        elif item_id == 'lock_timeout' and value is not None:
            # Timeout options: 10, 30, 60, 120, 300 seconds
            options = [10, 30, 60, 120, 300]
            try:
                idx = options.index(value)
            except ValueError:
                idx = 1
            
            if increase:
                idx = min(len(options) - 1, idx + 1)
            else:
                idx = max(0, idx - 1)
            
            new_val = options[idx]
            lock_app = self.ui.apps.get('lockscreen')
            if lock_app:
                lock_app.set_timeout(new_val)
            
            self.submenu_items[self.submenu_index] = (
                'lock_timeout', f'Timeout: {new_val}s', new_val
            )
    
    def _handle_submenu_action(self):
        """Handle action on selected submenu item."""
        if not self.submenu_items:
            return
        
        item_id = self.submenu_items[self.submenu_index][0]
        
        if item_id == 'wifi_config':
            # TODO: Launch WiFi configuration
            pass
        elif item_id == 'bt_scan':
            # TODO: Scan for Bluetooth devices
            pass
        elif item_id == 'lock_set_passcode':
            self.entering_passcode = True
            self.new_passcode = ""
        elif item_id == 'lock_clear_passcode':
            lock_app = self.ui.apps.get('lockscreen')
            if lock_app:
                lock_app.set_passcode(None)
                self.submenu_items[1] = ('lock_passcode', 'Passcode: None', None)
        elif item_id == 'lock_set_bg':
            # Use OSK to enter background image path
            lock_app = self.ui.apps.get('lockscreen')
            current_path = lock_app.background_image_path if lock_app and lock_app.background_image_path else ""
            self.ui.show_osk(
                "Background Image Path",
                current_path,
                lambda path: self._set_background_image(path),
                max_length=200
            )
        elif item_id == 'lock_clear_bg':
            lock_app = self.ui.apps.get('lockscreen')
            if lock_app:
                lock_app.clear_background_image()
                # Update menu item
                for i, item in enumerate(self.submenu_items):
                    if item[0] == 'lock_bg_image':
                        self.submenu_items[i] = ('lock_bg_image', 'Background: None', None)
                        break
        elif item_id == 'lock_now':
            lock_app = self.ui.apps.get('lockscreen')
            if lock_app:
                lock_app.lock()
    
    def on_click(self, x: int, y: int) -> bool:
        # Calculate which item was clicked
        item_height = 35
        start_y = self.ui.STATUS_BAR_HEIGHT + 10
        
        items = self.submenu_items if self.in_submenu else self.menu_items
        
        for i, item in enumerate(items):
            y1 = start_y + i * item_height
            if y1 <= y < y1 + item_height:
                if self.in_submenu:
                    self.submenu_index = i
                    self._handle_submenu_action()
                else:
                    self.selected_index = i
                    self._open_submenu(item[0])
                return True
        
        return False
    
    def _set_background_image(self, path: str):
        """Set background image path for lock screen."""
        lock_app = self.ui.apps.get('lockscreen')
        if lock_app:
            lock_app.set_background_image(path)
            # Update menu item
            bg_status = 'Set' if path else 'None'
            for i, item in enumerate(self.submenu_items):
                if item[0] == 'lock_bg_image':
                    self.submenu_items[i] = ('lock_bg_image', f'Background: {bg_status}', None)
                    break
    
    def draw(self, display: Display):
        """Draw settings screen."""
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        # Title
        title = 'Settings'
        if self.in_submenu and self.menu_items:
            title = self.menu_items[self.selected_index][1]
        
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, title, 
                    'white', 16)
        
        # Back hint for submenu
        if self.in_submenu:
            display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                        '< ESC', '#666666', 12, 'rt')
        
        # Menu items
        items = self.submenu_items if self.in_submenu else self.menu_items
        selected = self.submenu_index if self.in_submenu else self.selected_index
        scroll = self.submenu_scroll if self.in_submenu else self.scroll_offset
        
        item_height = 35
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        available_height = display.height - self.ui.STATUS_BAR_HEIGHT - 30
        max_visible = available_height // item_height
        
        # Draw only visible items
        for i in range(max_visible):
            item_idx = scroll + i
            if item_idx >= len(items):
                break
            
            item = items[item_idx]
            y = start_y + i * item_height
            is_selected = (item_idx == selected)
            
            if is_selected:
                display.rect(5, y, display.width - 10, item_height - 2,
                            fill='#0066cc')
            
            # Icon (if main menu)
            if not self.in_submenu and len(item) > 2:
                display.text(15, y + item_height // 2, item[2], 
                            'white', 16, 'lm')
                display.text(45, y + item_height // 2, item[1],
                            'white', 14, 'lm')
            else:
                display.text(15, y + item_height // 2, item[1],
                            'white', 14, 'lm')
            
            # Arrow for adjustable values
            if self.in_submenu and item[2] is not None:
                display.text(display.width - 15, y + item_height // 2,
                            '◀ ▶', '#888888', 12, 'rm')
        
        # Scroll indicators
        if scroll > 0:
            display.text(display.width // 2, start_y - 8, '▲', '#888888', 12, 'mm')
        
        if scroll + max_visible < len(items):
            display.text(display.width // 2, display.height - 8, '▼', '#888888', 12, 'mm')
        
        # Passcode entry overlay
        if self.entering_passcode:
            display.rect(20, display.height // 2 - 40, 
                        display.width - 40, 80, fill='#1a1a2e', color='#0066cc')
            display.text(display.width // 2, display.height // 2 - 20,
                        'Enter 4-digit passcode', 'white', 14, 'mm')
            
            # Show dots
            dot_spacing = 25
            start_x = display.width // 2 - int(dot_spacing * 1.5)
            for i in range(4):
                x = start_x + i * dot_spacing
                if i < len(self.new_passcode):
                    display.circle(x, display.height // 2 + 10, 8, fill='white')
                else:
                    display.circle(x, display.height // 2 + 10, 8, color='#666666', width=2)

