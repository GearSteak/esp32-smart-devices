"""
Calendar Application

Shows calendar view with:
- Month view
- Day view with events
- Event creation/editing
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import calendar
from datetime import datetime, timedelta
import json
import os


class CalendarApp(App):
    """Calendar application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='calendar',
            name='Calendar',
            icon='📅',
            color='#ff6b6b'
        )
        
        self.events_dir = ui.config.get('paths', {}).get('calendar', './data/calendar')
        self.events = {}  # {date_str: [events]}
        
        self.now = datetime.now()
        self.selected_year = self.now.year
        self.selected_month = self.now.month
        self.selected_day = self.now.day
        
        self.mode = 'month'  # 'month', 'day', 'event'
        self.selected_row = 0
        self.selected_col = 0
    
    def on_enter(self):
        """Load calendar data."""
        os.makedirs(self.events_dir, exist_ok=True)
        self._load_events()
        self.now = datetime.now()
        self.selected_year = self.now.year
        self.selected_month = self.now.month
        self.selected_day = self.now.day
        self.mode = 'month'
        self._update_selection_from_day()
    
    def on_exit(self):
        pass
    
    def _load_events(self):
        """Load events from disk."""
        self.events = {}
        events_file = os.path.join(self.events_dir, 'events.json')
        
        if os.path.exists(events_file):
            try:
                with open(events_file, 'r') as f:
                    self.events = json.load(f)
            except Exception as e:
                print(f"Error loading events: {e}")
    
    def _save_events(self):
        """Save events to disk."""
        events_file = os.path.join(self.events_dir, 'events.json')
        try:
            with open(events_file, 'w') as f:
                json.dump(self.events, f)
        except Exception as e:
            print(f"Error saving events: {e}")
    
    def _update_selection_from_day(self):
        """Update row/col selection from selected day."""
        cal = calendar.Calendar(firstweekday=6)  # Sunday first
        month_days = cal.monthdayscalendar(self.selected_year, self.selected_month)
        
        for row_idx, week in enumerate(month_days):
            for col_idx, day in enumerate(week):
                if day == self.selected_day:
                    self.selected_row = row_idx
                    self.selected_col = col_idx
                    return
    
    def _get_day_from_selection(self) -> int:
        """Get day number from current row/col selection."""
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.selected_year, self.selected_month)
        
        if self.selected_row < len(month_days):
            day = month_days[self.selected_row][self.selected_col]
            return day if day > 0 else 0
        return 0
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'month':
            return self._handle_month_key(event)
        elif self.mode == 'day':
            return self._handle_day_key(event)
        return False
    
    def _handle_month_key(self, event: KeyEvent) -> bool:
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.selected_year, self.selected_month)
        
        if event.code == KeyCode.UP:
            if self.selected_row > 0:
                self.selected_row -= 1
                day = self._get_day_from_selection()
                if day > 0:
                    self.selected_day = day
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_row < len(month_days) - 1:
                self.selected_row += 1
                day = self._get_day_from_selection()
                if day > 0:
                    self.selected_day = day
            return True
        elif event.code == KeyCode.LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
                day = self._get_day_from_selection()
                if day > 0:
                    self.selected_day = day
            else:
                # Previous month
                self._prev_month()
            return True
        elif event.code == KeyCode.RIGHT:
            if self.selected_col < 6:
                self.selected_col += 1
                day = self._get_day_from_selection()
                if day > 0:
                    self.selected_day = day
            else:
                # Next month
                self._next_month()
            return True
        elif event.code == KeyCode.ENTER:
            if self.selected_day > 0:
                self.mode = 'day'
            return True
        elif event.code == KeyCode.PAGEUP:
            self._prev_month()
            return True
        elif event.code == KeyCode.PAGEDOWN:
            self._next_month()
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def _handle_day_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.mode = 'month'
            return True
        elif event.char == 'n' or event.char == 'N':
            # TODO: Create new event
            return True
        return False
    
    def _prev_month(self):
        """Go to previous month."""
        if self.selected_month == 1:
            self.selected_month = 12
            self.selected_year -= 1
        else:
            self.selected_month -= 1
        self.selected_day = 1
        self._update_selection_from_day()
    
    def _next_month(self):
        """Go to next month."""
        if self.selected_month == 12:
            self.selected_month = 1
            self.selected_year += 1
        else:
            self.selected_month += 1
        self.selected_day = 1
        self._update_selection_from_day()
    
    def _has_events(self, day: int) -> bool:
        """Check if a day has events."""
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        return date_str in self.events and len(self.events[date_str]) > 0
    
    def draw(self, display: Display):
        """Draw calendar."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        if self.mode == 'month':
            self._draw_month(display)
        elif self.mode == 'day':
            self._draw_day(display)
    
    def _draw_month(self, display: Display):
        """Draw month view."""
        # Month/year header
        month_name = calendar.month_name[self.selected_month]
        header = f"{month_name} {self.selected_year}"
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 10,
                    header, 'white', 16, 'mm')
        
        # Navigation hints
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 10, '◀', '#666666', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 10, 
                    '▶', '#666666', 14, 'rt')
        
        # Day headers
        days = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
        cell_width = display.width // 7
        header_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        for i, day_name in enumerate(days):
            x = i * cell_width + cell_width // 2
            display.text(x, header_y, day_name, '#888888', 12, 'mm')
        
        # Calendar grid
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.selected_year, self.selected_month)
        
        cell_height = 32
        start_y = header_y + 15
        
        for row_idx, week in enumerate(month_days):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue
                
                x = col_idx * cell_width + cell_width // 2
                y = start_y + row_idx * cell_height
                
                # Selection highlight
                is_selected = (row_idx == self.selected_row and 
                              col_idx == self.selected_col and
                              day == self.selected_day)
                
                # Today highlight
                is_today = (day == self.now.day and 
                           self.selected_month == self.now.month and
                           self.selected_year == self.now.year)
                
                if is_selected:
                    display.circle(x, y + 8, 14, fill='#0066cc')
                elif is_today:
                    display.circle(x, y + 8, 14, color='#ff6b6b', width=2)
                
                # Day number
                color = 'white' if is_selected else ('#ff6b6b' if is_today else 'white')
                display.text(x, y + 8, str(day), color, 12, 'mm')
                
                # Event indicator
                if self._has_events(day):
                    display.circle(x, y + 20, 2, fill='#ffcc00')
    
    def _draw_day(self, display: Display):
        """Draw day view with events."""
        # Header
        date = datetime(self.selected_year, self.selected_month, self.selected_day)
        header = date.strftime('%A, %B %d')
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, header, 'white', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'ESC: Back', '#666666', 10, 'rt')
        
        # Events
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{self.selected_day:02d}"
        day_events = self.events.get(date_str, [])
        
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        if not day_events:
            display.text(display.width // 2, start_y + 30,
                        'No events', '#666666', 14, 'mm')
            display.text(display.width // 2, start_y + 50,
                        'Press N to add one', '#666666', 12, 'mm')
        else:
            for i, event in enumerate(day_events):
                y = start_y + i * 35
                
                # Time
                time_str = event.get('time', '')
                if time_str:
                    display.text(10, y + 10, time_str, '#888888', 11)
                
                # Title
                title = event.get('title', 'Event')[:25]
                display.text(60 if time_str else 10, y + 10, title, 'white', 13)

