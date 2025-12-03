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
            ('sound', 'Sound', '🔊'),
            ('gps', 'GPS', '📍'),
            ('apps', 'Apps', '📱'),
            ('about', 'About', 'ℹ'),
        ]
        
        self.selected_index = 0
        self.in_submenu = False
        self.submenu_items = []
        self.submenu_index = 0
    
    def on_enter(self):
        """Setup settings menu."""
        self.selected_index = 0
        self.in_submenu = False
    
    def on_exit(self):
        pass
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.in_submenu:
            return self._handle_submenu_key(event)
        
        if event.code == KeyCode.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_index < len(self.menu_items) - 1:
                self.selected_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            self._open_submenu(self.menu_items[self.selected_index][0])
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def _handle_submenu_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.submenu_index > 0:
                self.submenu_index -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.submenu_index < len(self.submenu_items) - 1:
                self.submenu_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            self._handle_submenu_action()
            return True
        elif event.code == KeyCode.ESC:
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
        
        item_height = 35
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        for i, item in enumerate(items):
            y = start_y + i * item_height
            is_selected = (i == selected)
            
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

