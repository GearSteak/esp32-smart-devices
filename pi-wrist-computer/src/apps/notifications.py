"""
Notifications App
Displays notifications from connected iOS device via ANCS BLE.
"""

import time
from typing import Optional, List, Dict
from datetime import datetime
from ..ui.framework import App, AppInfo
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode


class Notification:
    """Represents a notification."""
    
    def __init__(self, uid: int, title: str, message: str, app_name: str = "",
                 timestamp: Optional[datetime] = None):
        self.uid = uid
        self.title = title
        self.message = message
        self.app_name = app_name
        self.timestamp = timestamp or datetime.now()
        self.read = False
    
    def get_age_str(self) -> str:
        """Get human-readable age string."""
        delta = datetime.now() - self.timestamp
        seconds = int(delta.total_seconds())
        
        if seconds < 60:
            return "now"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        else:
            days = seconds // 86400
            return f"{days}d ago"


class NotificationsApp(App):
    """
    Notifications viewer
    
    Shows notifications received from iOS via ANCS BLE.
    Works with the ANCS service in services/ancs.py
    """
    
    # App icon mapping (approximate)
    APP_ICONS = {
        'messages': '💬',
        'mail': '📧',
        'phone': '📞',
        'calendar': '📅',
        'reminders': '📝',
        'twitter': '🐦',
        'instagram': '📷',
        'facebook': '👤',
        'whatsapp': '💬',
        'telegram': '✈️',
        'slack': '💼',
        'discord': '🎮',
    }
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='notifications',
            name='Notifications',
            icon='🔔',
            color='#e74c3c'
        )
        self.notifications: List[Notification] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.mode = 'list'  # list, detail
        self.current_notification: Optional[Notification] = None
        
        # For demo/testing - normally populated by ANCS service
        self._add_demo_notifications()
    
    def _add_demo_notifications(self):
        """Add demo notifications for testing."""
        self.notifications = [
            Notification(1, "John Doe", "Hey, are you coming to the game tonight?", "Messages",
                        datetime.now()),
            Notification(2, "Calendar", "Meeting in 15 minutes: Sprint Planning", "Calendar",
                        datetime.now()),
            Notification(3, "Mail", "New email from boss@company.com", "Mail",
                        datetime.now()),
        ]
    
    def add_notification(self, notification: Notification):
        """Add a new notification (called by ANCS service)."""
        # Check for duplicate
        for n in self.notifications:
            if n.uid == notification.uid:
                return
        
        self.notifications.insert(0, notification)
        
        # Limit stored notifications
        if len(self.notifications) > 50:
            self.notifications.pop()
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self.notifications if not n.read)
    
    def on_enter(self):
        """Called when app becomes active."""
        self.mode = 'list'
        self.selected_index = 0
        self.scroll_offset = 0
    
    def on_exit(self):
        """Called when leaving app."""
        pass
    
    def handle_input(self, event: KeyEvent) -> bool:
        """Handle input events."""
        if event.type != 'press':
            return False
        
        if self.mode == 'list':
            return self._handle_list_input(event)
        elif self.mode == 'detail':
            return self._handle_detail_input(event)
        
        return False
    
    def _handle_list_input(self, event: KeyEvent) -> bool:
        """Handle list view input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.ui.go_back()
            return True
        
        if not self.notifications:
            return False
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.notifications) - 1, self.selected_index + 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.ENTER:
            self._view_notification()
            return True
        elif event.char == 'd' or event.char == 'D' or event.code == KeyCode.DELETE:
            self._delete_notification()
            return True
        elif event.char == 'c' or event.char == 'C':
            self._clear_all()
            return True
        
        return False
    
    def _handle_detail_input(self, event: KeyEvent) -> bool:
        """Handle detail view input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'list'
            self.current_notification = None
            return True
        elif event.char == 'd' or event.char == 'D':
            self._delete_notification()
            self.mode = 'list'
            return True
        
        return False
    
    def _adjust_scroll(self):
        """Adjust scroll to keep selection visible."""
        max_visible = 6
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
    
    def _view_notification(self):
        """View selected notification."""
        if not self.notifications:
            return
        
        self.current_notification = self.notifications[self.selected_index]
        self.current_notification.read = True
        self.mode = 'detail'
    
    def _delete_notification(self):
        """Delete selected notification."""
        if not self.notifications:
            return
        
        del self.notifications[self.selected_index]
        self.selected_index = min(self.selected_index, len(self.notifications) - 1)
        self.selected_index = max(0, self.selected_index)
    
    def _clear_all(self):
        """Clear all notifications."""
        self.notifications = []
        self.selected_index = 0
        self.scroll_offset = 0
    
    def _get_app_icon(self, app_name: str) -> str:
        """Get icon for app."""
        app_lower = app_name.lower()
        for key, icon in self.APP_ICONS.items():
            if key in app_lower:
                return icon
        return '📱'
    
    def draw(self, display: Display):
        """Draw the notifications interface."""
        if self.mode == 'list':
            self._draw_list(display)
        elif self.mode == 'detail':
            self._draw_detail(display)
    
    def _draw_list(self, display: Display):
        """Draw notification list."""
        # Header
        unread = self.get_unread_count()
        header_text = f"🔔 Notifications ({unread})" if unread > 0 else "🔔 Notifications"
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    header_text, 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        if not self.notifications:
            display.text(display.width // 2, display.height // 2,
                        "No notifications", '#888888', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 25,
                        "All caught up! 🎉", '#666666', 12, 'mm')
            return
        
        # Draw notifications
        item_height = 45
        max_visible = 6
        
        for i in range(max_visible):
            idx = self.scroll_offset + i
            if idx >= len(self.notifications):
                break
            
            notif = self.notifications[idx]
            y = content_y + i * item_height
            
            selected = (idx == self.selected_index)
            if selected:
                display.rect(0, y, display.width, item_height - 2, fill='#0066cc')
            elif not notif.read:
                display.rect(0, y, display.width, item_height - 2, fill='#1a2a3a')
            
            # App icon
            icon = self._get_app_icon(notif.app_name)
            display.text(15, y + item_height // 2, icon, 'white', 18, 'mm')
            
            # Title and preview
            display.text(40, y + 10, notif.title[:25], 'white' if selected else '#dddddd', 12)
            display.text(40, y + 26, notif.message[:30] + "...", '#888888', 10)
            
            # Time
            display.text(display.width - 10, y + 10, notif.get_age_str(), '#666666', 9, 'rt')
            
            # Unread indicator
            if not notif.read:
                display.circle(display.width - 10, y + 25, 4, fill='#0088ff')
        
        # Scroll indicator
        if len(self.notifications) > max_visible:
            scroll_pct = self.scroll_offset / max(1, len(self.notifications) - max_visible)
            scroll_y = content_y + int(scroll_pct * (item_height * max_visible - 30))
            display.rect(display.width - 3, scroll_y, 2, 30, fill='#444444')
        
        # Help
        display.text(display.width // 2, display.height - 12,
                    "⏎:View  D:Delete  C:Clear All", '#555555', 9, 'mm')
    
    def _draw_detail(self, display: Display):
        """Draw notification detail."""
        if not self.current_notification:
            return
        
        notif = self.current_notification
        
        # Header
        icon = self._get_app_icon(notif.app_name)
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        display.text(15, self.ui.STATUS_BAR_HEIGHT + 14, icon, 'white', 18, 'lm')
        display.text(45, self.ui.STATUS_BAR_HEIGHT + 14, notif.app_name, 'white', 14, 'lm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 14, 
                    notif.get_age_str(), '#888888', 10, 'rm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 40
        
        # Title
        display.text(10, content_y, notif.title, 'white', 14)
        
        # Message (word wrap)
        y = content_y + 25
        words = notif.message.split()
        line = ""
        line_height = 16
        
        for word in words:
            test_line = f"{line} {word}".strip()
            # Approximate width check
            if len(test_line) > 35:
                display.text(10, y, line, '#cccccc', 12)
                y += line_height
                line = word
            else:
                line = test_line
        
        if line:
            display.text(10, y, line, '#cccccc', 12)
        
        # Help
        display.text(display.width // 2, display.height - 12,
                    "ESC:Back  D:Delete", '#555555', 9, 'mm')

