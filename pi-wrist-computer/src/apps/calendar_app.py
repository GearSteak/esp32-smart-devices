"""
Calendar Application

Shows calendar view with:
- Month view
- Day view with events
- Event creation/editing
- Google Calendar sync via Device Flow
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from ..services.google_auth import create_calendar_auth, GoogleDeviceAuth
import calendar
from datetime import datetime, timedelta
import json
import os
import requests


class CalendarApp(App):
    """Calendar application with optional Google Calendar sync."""
    
    GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
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
        self.google_events = {}  # Synced from Google
        
        self.now = datetime.now()
        self.selected_year = self.now.year
        self.selected_month = self.now.month
        self.selected_day = self.now.day
        
        self.mode = 'month'  # 'month', 'day', 'event', 'google_auth'
        self.selected_row = 0
        self.selected_col = 0
        
        # Google Calendar via Device Flow
        self.google_auth: GoogleDeviceAuth = None
        self.google_user_code = ""
        self.google_verification_url = ""
        self.sync_message = ""
        self.last_sync = None
        self.auth_status = ""  # For showing auth progress
    
    def on_enter(self):
        """Load calendar data."""
        os.makedirs(self.events_dir, exist_ok=True)
        self._load_events()
        self._init_google_calendar()
        self.now = datetime.now()
        self.selected_year = self.now.year
        self.selected_month = self.now.month
        self.selected_day = self.now.day
        self.mode = 'month'
        self._update_selection_from_day()
    
    def _init_google_calendar(self):
        """Initialize Google Calendar connection using Device Flow."""
        # Create auth handler with callbacks
        self.google_auth = create_calendar_auth(
            on_code_received=self._on_google_code,
            on_auth_complete=self._on_google_auth_complete,
            on_auth_error=self._on_google_auth_error
        )
        
        if self.google_auth is None:
            self.sync_message = "No credentials file"
            return
        
        # Check if already authenticated
        if self.google_auth.is_authenticated():
            self.auth_status = "Connected"
            self._sync_google_calendar()
    
    def _on_google_code(self, user_code: str, verification_url: str):
        """Called when device code is ready."""
        self.google_user_code = user_code
        self.google_verification_url = verification_url
        self.auth_status = "waiting_for_code"
        self.mode = 'google_auth'
    
    def _on_google_auth_complete(self, token_data: dict):
        """Called when authentication completes."""
        self.auth_status = "Connected"
        self.sync_message = "Google connected!"
        self.mode = 'month'
        self._sync_google_calendar()
    
    def _on_google_auth_error(self, error: str):
        """Called on authentication error."""
        self.auth_status = f"Error: {error[:20]}"
        self.sync_message = error
        self.mode = 'month'
    
    def _start_google_auth(self):
        """Start Google authentication flow."""
        if self.google_auth is None:
            self._init_google_calendar()
        
        if self.google_auth:
            self.auth_status = "Starting auth..."
            self.google_auth.start_auth()
    
    def _sync_google_calendar(self):
        """Sync events from Google Calendar using REST API."""
        if not self.google_auth or not self.google_auth.is_authenticated():
            self.sync_message = "Not authenticated"
            return
        
        access_token = self.google_auth.get_access_token()
        if not access_token:
            self.sync_message = "No access token"
            return
        
        try:
            # Get events for current month +/- 1 month
            start_date = datetime(self.selected_year, self.selected_month, 1)
            if self.selected_month == 1:
                start_date = datetime(self.selected_year - 1, 12, 1)
            else:
                start_date = datetime(self.selected_year, self.selected_month - 1, 1)
            
            end_date = start_date + timedelta(days=90)
            
            # Use REST API directly
            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                'timeMin': start_date.isoformat() + 'Z',
                'timeMax': end_date.isoformat() + 'Z',
                'maxResults': 100,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                # Token expired, try to refresh
                if self.google_auth.refresh_token():
                    self._sync_google_calendar()
                else:
                    self.sync_message = "Auth expired"
                return
            
            if response.status_code != 200:
                self.sync_message = f"API error: {response.status_code}"
                return
            
            data = response.json()
            events = data.get('items', [])
            
            # Clear old Google events and add new ones
            self.google_events = {}
            
            for event in events:
                start = event.get('start', {})
                start_str = start.get('dateTime', start.get('date', ''))
                
                if not start_str:
                    continue
                
                # Parse date
                if 'T' in start_str:
                    try:
                        event_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        date_str = event_date.strftime('%Y-%m-%d')
                        time_str = event_date.strftime('%H:%M')
                    except:
                        continue
                else:
                    date_str = start_str
                    time_str = ''
                
                if date_str not in self.google_events:
                    self.google_events[date_str] = []
                
                self.google_events[date_str].append({
                    'title': event.get('summary', 'No Title'),
                    'time': time_str,
                    'source': 'google',
                    'location': event.get('location', ''),
                })
            
            self.last_sync = datetime.now()
            self.sync_message = f"Synced {len(events)} events"
            
        except Exception as e:
            print(f"Google Calendar sync error: {e}")
            self.sync_message = f"Sync failed: {str(e)[:25]}"
    
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
        elif self.mode == 'google_auth':
            return self._handle_google_auth_key(event)
        return False
    
    def _handle_google_auth_key(self, event: KeyEvent) -> bool:
        """Handle keys during Google auth."""
        if event.code == KeyCode.ESC:
            if self.google_auth:
                self.google_auth.cancel_auth()
            self.mode = 'month'
            self.auth_status = "Cancelled"
            return True
        return True
    
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
        elif event.char == 's' or event.char == 'S':
            # Sync with Google Calendar
            if self.google_auth and self.google_auth.is_authenticated():
                self._sync_google_calendar()
            return True
        elif event.char == 'g' or event.char == 'G':
            # Start Google authentication
            self._start_google_auth()
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
        """Check if a day has events (local or Google)."""
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        local = date_str in self.events and len(self.events[date_str]) > 0
        google = date_str in self.google_events and len(self.google_events[date_str]) > 0
        return local or google
    
    def _get_all_events(self, day: int) -> list:
        """Get all events for a day (local + Google)."""
        date_str = f"{self.selected_year}-{self.selected_month:02d}-{day:02d}"
        events = []
        
        # Add local events
        if date_str in self.events:
            for e in self.events[date_str]:
                e['source'] = 'local'
                events.append(e)
        
        # Add Google events
        if date_str in self.google_events:
            events.extend(self.google_events[date_str])
        
        # Sort by time
        events.sort(key=lambda x: x.get('time', '') or '99:99')
        
        return events
    
    def draw(self, display: Display):
        """Draw calendar."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        if self.mode == 'month':
            self._draw_month(display)
        elif self.mode == 'day':
            self._draw_day(display)
        elif self.mode == 'google_auth':
            self._draw_google_auth(display)
    
    def _draw_google_auth(self, display: Display):
        """Draw Google authentication screen."""
        center_y = display.height // 2
        
        # Title
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 30,
                    "Google Calendar Login", 'white', 16, 'mm')
        
        if self.google_user_code:
            # Show the code
            display.text(display.width // 2, center_y - 40,
                        "Go to:", '#888888', 12, 'mm')
            display.text(display.width // 2, center_y - 20,
                        self.google_verification_url, '#4285f4', 14, 'mm')
            
            display.text(display.width // 2, center_y + 10,
                        "Enter this code:", '#888888', 12, 'mm')
            
            # Big code display
            display.rect(40, center_y + 25, display.width - 80, 50, 
                        fill='#2a2a4a', outline='#4285f4')
            display.text(display.width // 2, center_y + 50,
                        self.google_user_code, '#ffffff', 24, 'mm')
            
            display.text(display.width // 2, center_y + 90,
                        "Waiting for authorization...", '#888888', 10, 'mm')
        else:
            display.text(display.width // 2, center_y,
                        self.auth_status or "Starting...", '#888888', 14, 'mm')
        
        display.text(display.width // 2, display.height - 20,
                    "ESC to cancel", '#666666', 10, 'mm')
    
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
        
        # Google sync indicator
        if self.google_auth and self.google_auth.is_authenticated():
            sync_icon = '✓' if self.last_sync else '🔗'
            display.text(display.width // 2 + 80, self.ui.STATUS_BAR_HEIGHT + 10,
                        sync_icon, '#4285f4', 10)
        
        # Sync status and controls at bottom
        if self.sync_message:
            display.text(display.width // 2, display.height - 15,
                        self.sync_message, '#666666', 9, 'mm')
        elif self.google_auth and self.google_auth.is_authenticated():
            display.text(display.width // 2, display.height - 15,
                        "S:Sync", '#666666', 9, 'mm')
        else:
            display.text(display.width // 2, display.height - 15,
                        "G:Connect Google", '#666666', 9, 'mm')
        
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
        
        # Events (combined local + Google)
        day_events = self._get_all_events(self.selected_day)
        
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        if not day_events:
            display.text(display.width // 2, start_y + 30,
                        'No events', '#666666', 14, 'mm')
            display.text(display.width // 2, start_y + 50,
                        'Press N to add one', '#666666', 12, 'mm')
        else:
            for i, event in enumerate(day_events):
                if i >= 7:  # Max visible events
                    display.text(display.width // 2, start_y + i * 35,
                                f'+{len(day_events) - 7} more...', '#888888', 10, 'mm')
                    break
                
                y = start_y + i * 35
                
                # Source indicator
                source = event.get('source', 'local')
                source_icon = '📍' if source == 'local' else '📅'
                source_color = '#ff6b6b' if source == 'local' else '#4285f4'
                
                # Time
                time_str = event.get('time', '')
                if time_str:
                    display.text(10, y + 10, time_str, '#888888', 11)
                
                # Title with source icon
                title = event.get('title', 'Event')[:22]
                display.text(60 if time_str else 10, y + 10, f"{source_icon} {title}", 'white', 12)
                
                # Location if present
                location = event.get('location', '')
                if location:
                    display.text(60 if time_str else 10, y + 24, f"📍 {location[:25]}", '#666666', 9)

