"""
UI Framework

Provides the core UI system with:
- App management
- Screen/Scene handling
- Widget system
- Cursor management
- Input routing
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from PIL import Image
import time

from .display import Display
from ..input.cardkb import CardKB, KeyEvent, KeyCode
from ..input.trackball import Trackball


@dataclass
class Rect:
    """Rectangle for layout."""
    x: int
    y: int
    width: int
    height: int
    
    def contains(self, px: int, py: int) -> bool:
        return (self.x <= px < self.x + self.width and 
                self.y <= py < self.y + self.height)
    
    @property
    def center(self) -> tuple:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class AppInfo:
    """Application metadata."""
    id: str
    name: str
    icon: str  # Single character or emoji
    color: str = '#ffffff'
    description: str = ''


class Widget(ABC):
    """Base class for UI widgets."""
    
    def __init__(self, rect: Rect):
        self.rect = rect
        self.visible = True
        self.focused = False
        self.enabled = True
    
    @abstractmethod
    def draw(self, display: Display):
        """Draw the widget."""
        pass
    
    def on_key(self, event: KeyEvent) -> bool:
        """Handle key event. Return True if consumed."""
        return False
    
    def on_click(self, x: int, y: int) -> bool:
        """Handle click at position. Return True if consumed."""
        return False
    
    def on_cursor_move(self, x: int, y: int):
        """Handle cursor movement."""
        pass


class Label(Widget):
    """Text label widget."""
    
    def __init__(self, rect: Rect, text: str, color: str = 'white', 
                 size: int = 14, align: str = 'left'):
        super().__init__(rect)
        self.text = text
        self.color = color
        self.size = size
        self.align = align
    
    def draw(self, display: Display):
        if not self.visible:
            return
        
        if self.align == 'center':
            anchor = 'mm'
            x = self.rect.center[0]
        elif self.align == 'right':
            anchor = 'rm'
            x = self.rect.x + self.rect.width
        else:
            anchor = 'lm'
            x = self.rect.x
        
        y = self.rect.center[1]
        display.text(x, y, self.text, self.color, self.size, anchor)


class Button(Widget):
    """Clickable button widget."""
    
    def __init__(self, rect: Rect, text: str, on_click: Callable = None):
        super().__init__(rect)
        self.text = text
        self._on_click = on_click
        self.hovered = False
    
    def draw(self, display: Display):
        if not self.visible:
            return
        display.draw_button(self.rect.x, self.rect.y, 
                           self.rect.width, self.rect.height,
                           self.text, self.focused or self.hovered, self.enabled)
    
    def on_click(self, x: int, y: int) -> bool:
        if self.enabled and self._on_click and self.rect.contains(x, y):
            self._on_click()
            return True
        return False
    
    def on_cursor_move(self, x: int, y: int):
        self.hovered = self.rect.contains(x, y)


class ListBox(Widget):
    """Scrollable list widget."""
    
    def __init__(self, rect: Rect, items: List[str] = None, 
                 item_height: int = 30, on_select: Callable = None):
        super().__init__(rect)
        self.items = items or []
        self.item_height = item_height
        self.selected_index = 0
        self.scroll_offset = 0
        self._on_select = on_select
    
    @property
    def visible_count(self) -> int:
        return self.rect.height // self.item_height
    
    def draw(self, display: Display):
        if not self.visible:
            return
        
        visible = self.visible_count
        for i in range(visible):
            item_idx = self.scroll_offset + i
            if item_idx >= len(self.items):
                break
            
            y = self.rect.y + i * self.item_height
            selected = item_idx == self.selected_index
            display.draw_list_item(
                self.rect.x, y, self.rect.width, self.item_height,
                self.items[item_idx], selected
            )
    
    def on_key(self, event: KeyEvent) -> bool:
        if not self.focused:
            return False
        
        if event.code == KeyCode.UP:
            self.select_prev()
            return True
        elif event.code == KeyCode.DOWN:
            self.select_next()
            return True
        elif event.code == KeyCode.ENTER:
            if self._on_select and 0 <= self.selected_index < len(self.items):
                self._on_select(self.selected_index, self.items[self.selected_index])
            return True
        
        return False
    
    def select_next(self):
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            # Scroll if needed
            if self.selected_index >= self.scroll_offset + self.visible_count:
                self.scroll_offset = self.selected_index - self.visible_count + 1
    
    def select_prev(self):
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index


class TextInput(Widget):
    """Text input field."""
    
    def __init__(self, rect: Rect, placeholder: str = '', multiline: bool = False):
        super().__init__(rect)
        self.text = ''
        self.placeholder = placeholder
        self.multiline = multiline
        self.cursor_pos = 0
        self._cursor_visible = True
        self._last_blink = 0
    
    def draw(self, display: Display):
        if not self.visible:
            return
        
        # Background
        bg = '#333333' if self.focused else '#222222'
        display.rect(self.rect.x, self.rect.y, 
                    self.rect.width, self.rect.height, 
                    fill=bg, color='#666666' if not self.focused else '#0088ff')
        
        # Text or placeholder
        text_display = self.text if self.text else self.placeholder
        color = 'white' if self.text else '#666666'
        display.text(self.rect.x + 5, self.rect.center[1], 
                    text_display, color, 14, 'lm')
        
        # Cursor
        if self.focused:
            now = time.time()
            if now - self._last_blink > 0.5:
                self._cursor_visible = not self._cursor_visible
                self._last_blink = now
            
            if self._cursor_visible:
                # Calculate cursor X position
                text_before = self.text[:self.cursor_pos]
                cursor_x = self.rect.x + 5 + len(text_before) * 8
                display.line(cursor_x, self.rect.y + 5, 
                            cursor_x, self.rect.y + self.rect.height - 5, 'white')
    
    def on_key(self, event: KeyEvent) -> bool:
        if not self.focused:
            return False
        
        if event.code == KeyCode.BACKSPACE:
            if self.cursor_pos > 0:
                self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                self.cursor_pos -= 1
            return True
        elif event.code == KeyCode.DEL:
            if self.cursor_pos < len(self.text):
                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            return True
        elif event.code == KeyCode.LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            return True
        elif event.code == KeyCode.RIGHT:
            if self.cursor_pos < len(self.text):
                self.cursor_pos += 1
            return True
        elif event.code == KeyCode.HOME:
            self.cursor_pos = 0
            return True
        elif event.code == KeyCode.END:
            self.cursor_pos = len(self.text)
            return True
        elif event.char:
            self.text = self.text[:self.cursor_pos] + event.char + self.text[self.cursor_pos:]
            self.cursor_pos += 1
            return True
        
        return False


class App(ABC):
    """Base class for applications."""
    
    def __init__(self, ui: 'UI'):
        self.ui = ui
        self.info: AppInfo = AppInfo(id='base', name='App', icon='?')
        self.widgets: List[Widget] = []
        self.focused_widget: Optional[Widget] = None
    
    @abstractmethod
    def on_enter(self):
        """Called when app becomes active."""
        pass
    
    @abstractmethod
    def on_exit(self):
        """Called when app is closed."""
        pass
    
    @abstractmethod
    def draw(self, display: Display):
        """Draw the app content."""
        pass
    
    def on_key(self, event: KeyEvent) -> bool:
        """Handle key input. Return True if consumed."""
        if self.focused_widget:
            return self.focused_widget.on_key(event)
        return False
    
    def on_click(self, x: int, y: int) -> bool:
        """Handle click. Return True if consumed."""
        for widget in self.widgets:
            if widget.visible and widget.on_click(x, y):
                return True
        return False
    
    def on_cursor_move(self, x: int, y: int):
        """Handle cursor movement."""
        for widget in self.widgets:
            if widget.visible:
                widget.on_cursor_move(x, y)
    
    def update(self, dt: float):
        """Update app state. dt = time since last update."""
        pass
    
    def focus_widget(self, widget: Widget):
        """Set focus to a widget."""
        if self.focused_widget:
            self.focused_widget.focused = False
        self.focused_widget = widget
        if widget:
            widget.focused = True
    
    def draw_widgets(self, display: Display):
        """Draw all widgets."""
        for widget in self.widgets:
            if widget.visible:
                widget.draw(display)


@dataclass
class Notification:
    """Notification data."""
    id: str
    title: str
    body: str
    icon: str = '!'
    color: str = '#0088ff'
    timestamp: float = 0
    duration: float = 5.0  # seconds
    read: bool = False  # Track if notification has been viewed


class UI:
    """Main UI manager."""
    
    STATUS_BAR_HEIGHT = 20
    
    def __init__(self, display: Display, cardkb: CardKB, trackball: Trackball,
                 usb_joystick=None, config: dict = None):
        self.display = display
        self.cardkb = cardkb
        self.trackball = trackball
        self.usb_joystick = usb_joystick
        self.config = config or {}
        
        # Screen dimensions (below status bar)
        self.content_rect = Rect(
            0, self.STATUS_BAR_HEIGHT,
            display.width, display.height - self.STATUS_BAR_HEIGHT
        )
        
        # App management
        self.apps: Dict[str, App] = {}
        self.current_app: Optional[App] = None
        self.home_app_id: str = 'home'
        
        # Cursor state
        self.cursor_x = display.width // 2
        self.cursor_y = display.height // 2
        self.cursor_visible = True
        self.cursor_size = config.get('cursor_size', 8)
        
        # Status bar state
        self.time_str = '00:00'
        self.wifi_connected = False
        self.bt_connected = False
        self.battery_percent = 100
        self.show_battery = config.get('show_battery', True)  # Can hide if no UPS
        
        # Notifications
        self.notifications: List[Notification] = []
        self.current_notification: Optional[Notification] = None
        self._notification_y = -50  # Animation offset
        
        # Timing
        self._last_update = time.time()
        
        # Setup input callbacks
        self._setup_input()
    
    def _setup_input(self):
        """Setup input handling."""
        self.cardkb.on_key(self._on_key)
        self.trackball.on_move(self._on_cursor_move)
        self.trackball.on_click(self._on_click)
        
        # Add USB joystick support if available
        if self.usb_joystick and self.usb_joystick.enabled:
            self.usb_joystick.on_move(self._on_cursor_move)
            self.usb_joystick.on_click(self._on_click)
    
    def _on_key(self, event: KeyEvent):
        """Handle keyboard input."""
        # Reset lock screen activity timer (only if lock screen is active)
        if self.current_app and self.current_app.info.id == 'lockscreen':
            lock_app = self.apps.get('lockscreen')
            if lock_app:
                lock_app.reset_activity()
        
        # Pass to current app first
        if self.current_app:
            handled = self.current_app.on_key(event)
            # If app handled ESC, don't do default behavior
            if handled and event.code == KeyCode.ESC:
                return
        
        # ESC returns to home (unless on lock screen or app already handled it)
        if event.code == KeyCode.ESC:
            if self.current_app and self.current_app.info.id != 'lockscreen':
                self.go_home()
            return
    
    def _on_cursor_move(self, x: int, y: int):
        """Handle cursor movement from trackball or USB joystick."""
        # Get movement from trackball
        dx, dy = self.trackball.get_delta()
        
        # Add movement from USB joystick if available
        if self.usb_joystick and self.usb_joystick.enabled:
            jx, jy = self.usb_joystick.get_delta()
            dx += jx
            dy += jy
        
        # Update cursor position
        self.cursor_x = max(0, min(self.display.width - 1, self.cursor_x + dx))
        self.cursor_y = max(self.STATUS_BAR_HEIGHT, 
                           min(self.display.height - 1, self.cursor_y + dy))
        
        # Notify current app
        if self.current_app:
            self.current_app.on_cursor_move(self.cursor_x, self.cursor_y)
    
    def _on_click(self, pressed: bool):
        """Handle trackball or USB joystick click."""
        # Reset lock screen activity timer (only if lock screen is active)
        if self.current_app and self.current_app.info.id == 'lockscreen':
            lock_app = self.apps.get('lockscreen')
            if lock_app:
                lock_app.reset_activity()
        
        if pressed and self.current_app:
            self.current_app.on_click(self.cursor_x, self.cursor_y)
    
    def register_app(self, app: App):
        """Register an application."""
        self.apps[app.info.id] = app
    
    def launch_app(self, app_id: str):
        """Launch an application."""
        if app_id not in self.apps:
            print(f"Unknown app: {app_id}")
            return
        
        # Exit current app
        if self.current_app:
            self.current_app.on_exit()
        
        # Reset lock screen activity timer when navigating
        lock_app = self.apps.get('lockscreen')
        if lock_app:
            lock_app.reset_activity()
        
        # Enter new app
        self.current_app = self.apps[app_id]
        self.current_app.on_enter()
    
    def go_home(self):
        """Return to home screen."""
        self.launch_app(self.home_app_id)
    
    def show_notification(self, notification: Notification):
        """Show a notification."""
        notification.timestamp = time.time()
        self.notifications.append(notification)
        
        if not self.current_notification:
            self._pop_notification()
    
    def _pop_notification(self):
        """Pop next notification to display."""
        if self.notifications:
            self.current_notification = self.notifications.pop(0)
            self._notification_y = -50
    
    def set_status(self, wifi: bool = None, bt: bool = None, 
                   battery: int = None, time_str: str = None):
        """Update status bar values."""
        if wifi is not None:
            self.wifi_connected = wifi
        if bt is not None:
            self.bt_connected = bt
        if battery is not None:
            self.battery_percent = battery
        if time_str is not None:
            self.time_str = time_str
    
    def update(self):
        """Update UI state."""
        now = time.time()
        dt = now - self._last_update
        self._last_update = now
        
        # Update current app
        if self.current_app:
            self.current_app.update(dt)
        
        # Update notification animation
        if self.current_notification:
            # Slide in
            if self._notification_y < 25:
                self._notification_y += dt * 200
            else:
                # Check if expired
                elapsed = now - self.current_notification.timestamp
                if elapsed > self.current_notification.duration:
                    self.current_notification = None
                    self._pop_notification()
        
        # Poll keyboard
        self.cardkb.poll()
    
    def draw(self):
        """Draw the entire UI."""
        self.display.clear()
        
        # Draw status bar
        # Count unread notifications
        notif_count = len([n for n in self.notifications if not n.read])
        
        self.display.draw_status_bar(
            self.time_str,
            self.wifi_connected,
            self.bt_connected,
            self.battery_percent if self.show_battery else None,
            notif_count
        )
        
        # Draw current app
        if self.current_app:
            self.current_app.draw(self.display)
        
        # Draw notification (slides in from top)
        if self.current_notification:
            self._draw_notification()
        
        # Draw cursor
        if self.cursor_visible:
            self.display.draw_cursor(self.cursor_x, self.cursor_y, self.cursor_size)
        
        # Push to display
        self.display.refresh()
    
    def _draw_notification(self):
        """Draw current notification."""
        n = self.current_notification
        if not n:
            return
        
        y = int(self._notification_y)
        w = self.display.width - 20
        h = 45
        x = 10
        
        # Background
        self.display.rect(x, y, w, h, fill='#1a1a1a', color=n.color, width=2)
        
        # Icon
        self.display.text(x + 10, y + h // 2, n.icon, n.color, 18, 'lm')
        
        # Title
        self.display.text(x + 35, y + 12, n.title, 'white', 12)
        
        # Body (truncate)
        max_chars = (w - 45) // 7
        body = n.body[:max_chars] + '...' if len(n.body) > max_chars else n.body
        self.display.text(x + 35, y + 28, body, '#aaaaaa', 11)
    
    def run(self):
        """Main loop."""
        try:
            while True:
                self.update()
                self.draw()
                time.sleep(1/60)  # ~60 FPS for better input responsiveness
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown."""
        if self.current_app:
            self.current_app.on_exit()
        self.display.shutdown()
        self.cardkb.shutdown()
        self.trackball.shutdown()

