"""
Clock Application

Features:
- Display current time and date
- Set alarms
- Set date and time
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from datetime import datetime, timedelta
import calendar
import json
import os
import subprocess


class ClockApp(App):
    """Clock application with alarms and time/date setting."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='clock',
            name='Clock',
            icon='🕐',
            color='#4a90e2'
        )
        
        self.alarms_file = os.path.expanduser('~/.piwrist_alarms.json')
        self.alarms = []
        self.mode = 'clock'  # 'clock', 'alarms', 'set_alarm', 'set_time', 'set_date'
        self.selected_index = 0
        self.scroll_offset = 0
        
        # Alarm editing
        self.editing_alarm = None
        self.alarm_hour = 12
        self.alarm_minute = 0
        self.alarm_enabled = True
        self.alarm_label = ""
        
        # Time/date editing
        self.editing_time = False
        self.editing_date = False
        self.edit_year = datetime.now().year
        self.edit_month = datetime.now().month
        self.edit_day = datetime.now().day
        self.edit_hour = datetime.now().hour
        self.edit_minute = datetime.now().minute
        self.edit_second = datetime.now().second
        self.edit_field = 'hour'  # 'hour', 'minute', 'second', 'year', 'month', 'day'
        
        self._load_alarms()
    
    def on_enter(self):
        """Called when app becomes active."""
        self.mode = 'clock'
        self.selected_index = 0
    
    def on_exit(self):
        """Called when app is closed."""
        self._save_alarms()
    
    def _load_alarms(self):
        """Load alarms from file."""
        try:
            if os.path.exists(self.alarms_file):
                with open(self.alarms_file, 'r') as f:
                    data = json.load(f)
                    self.alarms = data.get('alarms', [])
        except Exception as e:
            print(f"Error loading alarms: {e}")
            self.alarms = []
    
    def _save_alarms(self):
        """Save alarms to file."""
        try:
            with open(self.alarms_file, 'w') as f:
                json.dump({'alarms': self.alarms}, f)
        except Exception as e:
            print(f"Error saving alarms: {e}")
    
    def _check_alarms(self):
        """Check if any alarms should trigger."""
        now = datetime.now()
        for alarm in self.alarms:
            if not alarm.get('enabled', True):
                continue
            
            hour = alarm.get('hour', 0)
            minute = alarm.get('minute', 0)
            
            # Check if current time matches alarm (within 1 minute window)
            if now.hour == hour and now.minute == minute and now.second < 10:
                # Trigger alarm (could add sound/notification here)
                label = alarm.get('label', 'Alarm')
                self.ui.show_notification('Alarm', label, '🔔', '#ff6b6b')
    
    def _set_system_time(self, dt: datetime):
        """Set system date and time."""
        try:
            # Format: YYYY-MM-DD HH:MM:SS
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            # Use sudo date command (requires passwordless sudo or running as root)
            subprocess.run(['sudo', 'date', '-s', time_str], check=True)
            # Sync hardware clock
            subprocess.run(['sudo', 'hwclock', '--systohc'], check=True)
        except Exception as e:
            print(f"Error setting system time: {e}")
    
    def on_key(self, event: KeyEvent) -> bool:
        """Handle key input."""
        if self.mode == 'clock':
            if event.char == 'a' or event.char == 'A':
                self.mode = 'alarms'
                self.selected_index = 0
                self.scroll_offset = 0
                return True
            elif event.char == 't' or event.char == 'T':
                self.mode = 'set_time'
                self.editing_time = True
                now = datetime.now()
                self.edit_hour = now.hour
                self.edit_minute = now.minute
                self.edit_second = now.second
                self.edit_field = 'hour'
                return True
            elif event.char == 'd' or event.char == 'D':
                self.mode = 'set_date'
                self.editing_date = True
                now = datetime.now()
                self.edit_year = now.year
                self.edit_month = now.month
                self.edit_day = now.day
                self.edit_field = 'year'
                return True
            elif event.code == KeyCode.ESC:
                self.ui.go_home()
                return True
        
        elif self.mode == 'alarms':
            if event.code == KeyCode.UP:
                if self.selected_index > 0:
                    self.selected_index -= 1
                    if self.selected_index < self.scroll_offset:
                        self.scroll_offset = self.selected_index
                return True
            elif event.code == KeyCode.DOWN:
                if self.selected_index < len(self.alarms):
                    self.selected_index += 1
                    max_visible = 5
                    if self.selected_index >= self.scroll_offset + max_visible:
                        self.scroll_offset = self.selected_index - max_visible + 1
                return True
            elif event.code == KeyCode.ENTER:
                if self.selected_index < len(self.alarms):
                    # Edit existing alarm
                    self.editing_alarm = self.alarms[self.selected_index]
                    self.alarm_hour = self.editing_alarm.get('hour', 12)
                    self.alarm_minute = self.editing_alarm.get('minute', 0)
                    self.alarm_enabled = self.editing_alarm.get('enabled', True)
                    self.alarm_label = self.editing_alarm.get('label', '')
                    self.mode = 'set_alarm'
                else:
                    # Add new alarm
                    self.editing_alarm = None
                    self.alarm_hour = datetime.now().hour
                    self.alarm_minute = datetime.now().minute
                    self.alarm_enabled = True
                    self.alarm_label = ""
                    self.mode = 'set_alarm'
                return True
            elif event.char == 'd' or event.char == 'D':
                # Delete selected alarm
                if self.selected_index < len(self.alarms):
                    self.alarms.pop(self.selected_index)
                    if self.selected_index >= len(self.alarms):
                        self.selected_index = max(0, len(self.alarms) - 1)
                    self._save_alarms()
                return True
            elif event.code == KeyCode.ESC:
                self.mode = 'clock'
                return True
        
        elif self.mode == 'set_alarm':
            if event.code == KeyCode.LEFT:
                if self.edit_field == 'minute':
                    self.edit_field = 'hour'
                elif self.edit_field == 'label':
                    self.edit_field = 'minute'
                return True
            elif event.code == KeyCode.RIGHT:
                if self.edit_field == 'hour':
                    self.edit_field = 'minute'
                elif self.edit_field == 'minute':
                    self.edit_field = 'label'
                return True
            elif event.code == KeyCode.UP:
                if self.edit_field == 'hour':
                    self.alarm_hour = (self.alarm_hour + 1) % 24
                elif self.edit_field == 'minute':
                    self.alarm_minute = (self.alarm_minute + 1) % 60
                elif self.edit_field == 'label':
                    # Toggle enabled
                    self.alarm_enabled = not self.alarm_enabled
                return True
            elif event.code == KeyCode.DOWN:
                if self.edit_field == 'hour':
                    self.alarm_hour = (self.alarm_hour - 1) % 24
                elif self.edit_field == 'minute':
                    self.alarm_minute = (self.alarm_minute - 1) % 60
                elif self.edit_field == 'label':
                    # Toggle enabled
                    self.alarm_enabled = not self.alarm_enabled
                return True
            elif event.code == KeyCode.ENTER:
                # Save alarm
                if self.edit_field == 'label':
                    # Open OSK for label
                    self.ui.show_osk(
                        "Alarm Label",
                        self.alarm_label,
                        lambda label: self._save_alarm_with_label(label),
                        max_length=30
                    )
                else:
                    self._save_alarm()
                return True
            elif event.code == KeyCode.ESC:
                self.mode = 'alarms'
                return True
        
        elif self.mode == 'set_time':
            if event.code == KeyCode.LEFT:
                if self.edit_field == 'minute':
                    self.edit_field = 'hour'
                elif self.edit_field == 'second':
                    self.edit_field = 'minute'
                return True
            elif event.code == KeyCode.RIGHT:
                if self.edit_field == 'hour':
                    self.edit_field = 'minute'
                elif self.edit_field == 'minute':
                    self.edit_field = 'second'
                return True
            elif event.code == KeyCode.UP:
                if self.edit_field == 'hour':
                    self.edit_hour = (self.edit_hour + 1) % 24
                elif self.edit_field == 'minute':
                    self.edit_minute = (self.edit_minute + 1) % 60
                elif self.edit_field == 'second':
                    self.edit_second = (self.edit_second + 1) % 60
                return True
            elif event.code == KeyCode.DOWN:
                if self.edit_field == 'hour':
                    self.edit_hour = (self.edit_hour - 1) % 24
                elif self.edit_field == 'minute':
                    self.edit_minute = (self.edit_minute - 1) % 60
                elif self.edit_field == 'second':
                    self.edit_second = (self.edit_second - 1) % 60
                return True
            elif event.code == KeyCode.ENTER:
                # Set system time
                dt = datetime(self.edit_year, self.edit_month, self.edit_day,
                            self.edit_hour, self.edit_minute, self.edit_second)
                self._set_system_time(dt)
                self.mode = 'clock'
                return True
            elif event.code == KeyCode.ESC:
                self.mode = 'clock'
                return True
        
        elif self.mode == 'set_date':
            if event.code == KeyCode.LEFT:
                if self.edit_field == 'month':
                    self.edit_field = 'year'
                elif self.edit_field == 'day':
                    self.edit_field = 'month'
                return True
            elif event.code == KeyCode.RIGHT:
                if self.edit_field == 'year':
                    self.edit_field = 'month'
                elif self.edit_field == 'month':
                    self.edit_field = 'day'
                return True
            elif event.code == KeyCode.UP:
                if self.edit_field == 'year':
                    self.edit_year += 1
                elif self.edit_field == 'month':
                    self.edit_month = (self.edit_month % 12) + 1
                elif self.edit_field == 'day':
                    # Get max days in month
                    max_days = calendar.monthrange(self.edit_year, self.edit_month)[1]
                    self.edit_day = min(self.edit_day + 1, max_days)
                return True
            elif event.code == KeyCode.DOWN:
                if self.edit_field == 'year':
                    self.edit_year = max(2000, self.edit_year - 1)
                elif self.edit_field == 'month':
                    self.edit_month = ((self.edit_month - 2) % 12) + 1
                elif self.edit_field == 'day':
                    self.edit_day = max(1, self.edit_day - 1)
                return True
            elif event.code == KeyCode.ENTER:
                # Set system date
                dt = datetime(self.edit_year, self.edit_month, self.edit_day,
                            self.edit_hour, self.edit_minute, self.edit_second)
                self._set_system_time(dt)
                self.mode = 'clock'
                return True
            elif event.code == KeyCode.ESC:
                self.mode = 'clock'
                return True
        
        return False
    
    def _save_alarm(self):
        """Save current alarm."""
        alarm = {
            'hour': self.alarm_hour,
            'minute': self.alarm_minute,
            'enabled': self.alarm_enabled,
            'label': self.alarm_label
        }
        
        if self.editing_alarm:
            # Update existing
            idx = self.alarms.index(self.editing_alarm)
            self.alarms[idx] = alarm
        else:
            # Add new
            self.alarms.append(alarm)
        
        self._save_alarms()
        self.mode = 'alarms'
        self.selected_index = len(self.alarms) - 1
    
    def _save_alarm_with_label(self, label: str):
        """Save alarm after setting label."""
        self.alarm_label = label
        self._save_alarm()
    
    def update(self, dt: float):
        """Update app state."""
        if self.mode == 'clock':
            self._check_alarms()
    
    def draw(self, display: Display):
        """Draw clock screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a1628')
        
        if self.mode == 'clock':
            self._draw_clock(display)
        elif self.mode == 'alarms':
            self._draw_alarms(display)
        elif self.mode == 'set_alarm':
            self._draw_set_alarm(display)
        elif self.mode == 'set_time':
            self._draw_set_time(display)
        elif self.mode == 'set_date':
            self._draw_set_date(display)
    
    def _draw_clock(self, display: Display):
        """Draw main clock view."""
        now = datetime.now()
        
        # Large time
        time_str = now.strftime('%H:%M:%S')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 60,
                    time_str, 'white', 48, 'mm')
        
        # Date
        date_str = now.strftime('%A, %B %d, %Y')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 120,
                    date_str, '#aaaaaa', 14, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 30,
                    'A:Alarms T:Time D:Date', '#666666', 10, 'mm')
    
    def _draw_alarms(self, display: Display):
        """Draw alarms list."""
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Alarms', 'white', 16)
        
        # List alarms
        start_y = self.ui.STATUS_BAR_HEIGHT + 35
        item_height = 35
        max_visible = 5
        
        visible_start = self.scroll_offset
        visible_end = min(len(self.alarms) + 1, visible_start + max_visible)
        
        for i in range(visible_start, visible_end):
            y = start_y + (i - visible_start) * item_height
            
            if i < len(self.alarms):
                alarm = self.alarms[i]
                hour = alarm.get('hour', 0)
                minute = alarm.get('minute', 0)
                enabled = alarm.get('enabled', True)
                label = alarm.get('label', '')
                
                status = '✓' if enabled else '✗'
                time_str = f"{hour:02d}:{minute:02d}"
                
                if i == self.selected_index:
                    display.rect(5, y - 2, display.width - 10, item_height - 4,
                                fill='#333333', outline='#555555')
                
                display.text(15, y + item_height // 2, status, '#4a90e2' if enabled else '#666666', 14, 'lm')
                display.text(35, y + item_height // 2, time_str, 'white', 14, 'lm')
                if label:
                    display.text(100, y + item_height // 2, label, '#aaaaaa', 12, 'lm')
            else:
                # "Add new" option
                if i == self.selected_index:
                    display.rect(5, y - 2, display.width - 10, item_height - 4,
                                fill='#333333', outline='#555555')
                display.text(15, y + item_height // 2, '+ Add Alarm', '#888888', 14, 'lm')
        
        # Scroll indicators
        if self.scroll_offset > 0:
            display.text(display.width // 2, start_y - 15, '▲', '#666666', 12, 'mm')
        if visible_end < len(self.alarms) + 1:
            display.text(display.width // 2, start_y + max_visible * item_height + 5, '▼', '#666666', 12, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 20,
                    'Enter:Edit D:Delete ESC:Back', '#666666', 9, 'mm')
    
    def _draw_set_alarm(self, display: Display):
        """Draw alarm setting screen."""
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Set Alarm', 'white', 16)
        
        y = self.ui.STATUS_BAR_HEIGHT + 50
        
        # Hour
        hour_color = '#4a90e2' if self.edit_field == 'hour' else 'white'
        display.text(display.width // 2 - 40, y, f"{self.alarm_hour:02d}", hour_color, 32, 'mm')
        
        # Colon
        display.text(display.width // 2, y, ':', 'white', 32, 'mm')
        
        # Minute
        minute_color = '#4a90e2' if self.edit_field == 'minute' else 'white'
        display.text(display.width // 2 + 40, y, f"{self.alarm_minute:02d}", minute_color, 32, 'mm')
        
        # Enabled
        y += 50
        enabled_color = '#4a90e2' if self.edit_field == 'label' else 'white'
        status = 'Enabled' if self.alarm_enabled else 'Disabled'
        display.text(display.width // 2, y, f"Status: {status}", enabled_color, 16, 'mm')
        
        # Label
        y += 30
        label_text = self.alarm_label if self.alarm_label else 'No label'
        label_color = '#4a90e2' if self.edit_field == 'label' else '#aaaaaa'
        display.text(display.width // 2, y, f"Label: {label_text}", label_color, 14, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 20,
                    '↑↓:Adjust ←→:Field Enter:Save', '#666666', 9, 'mm')
    
    def _draw_set_time(self, display: Display):
        """Draw time setting screen."""
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Set Time', 'white', 16)
        
        y = self.ui.STATUS_BAR_HEIGHT + 60
        
        # Time display
        hour_color = '#4a90e2' if self.edit_field == 'hour' else 'white'
        minute_color = '#4a90e2' if self.edit_field == 'minute' else 'white'
        second_color = '#4a90e2' if self.edit_field == 'second' else 'white'
        
        display.text(display.width // 2 - 50, y, f"{self.edit_hour:02d}", hour_color, 32, 'mm')
        display.text(display.width // 2 - 10, y, ':', 'white', 32, 'mm')
        display.text(display.width // 2 + 20, y, f"{self.edit_minute:02d}", minute_color, 32, 'mm')
        display.text(display.width // 2 + 60, y, ':', 'white', 32, 'mm')
        display.text(display.width // 2 + 80, y, f"{self.edit_second:02d}", second_color, 32, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 20,
                    '↑↓:Adjust ←→:Field Enter:Set ESC:Cancel', '#666666', 9, 'mm')
    
    def _draw_set_date(self, display: Display):
        """Draw date setting screen."""
        import calendar
        
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Set Date', 'white', 16)
        
        y = self.ui.STATUS_BAR_HEIGHT + 60
        
        # Date display
        year_color = '#4a90e2' if self.edit_field == 'year' else 'white'
        month_color = '#4a90e2' if self.edit_field == 'month' else 'white'
        day_color = '#4a90e2' if self.edit_field == 'day' else 'white'
        
        month_name = calendar.month_name[self.edit_month]
        display.text(display.width // 2, y, f"{self.edit_year}", year_color, 24, 'mm')
        display.text(display.width // 2, y + 35, f"{month_name}", month_color, 20, 'mm')
        display.text(display.width // 2, y + 60, f"{self.edit_day:02d}", day_color, 24, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 20,
                    '↑↓:Adjust ←→:Field Enter:Set ESC:Cancel', '#666666', 9, 'mm')

