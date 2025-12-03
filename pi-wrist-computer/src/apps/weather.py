"""
Weather Application

Shows weather data from OpenWeatherMap API.
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import requests
import json
import os
from datetime import datetime


class WeatherApp(App):
    """Weather application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='weather',
            name='Weather',
            icon='🌤',
            color='#4dc9ff'
        )
        
        self.api_key = ui.config.get('apps', {}).get('weather', {}).get('api_key', '')
        self.location = ui.config.get('apps', {}).get('weather', {}).get('location', '')
        
        self.weather_data = None
        self.forecast = []
        self.last_update = None
        self.loading = False
        self.error = None
    
    def on_enter(self):
        """Fetch weather on enter."""
        if not self.weather_data or self._should_refresh():
            self._fetch_weather()
    
    def on_exit(self):
        pass
    
    def _should_refresh(self) -> bool:
        """Check if weather should be refreshed."""
        if not self.last_update:
            return True
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed > 1800  # 30 minutes
    
    def _fetch_weather(self):
        """Fetch weather data from API."""
        if not self.api_key or not self.location:
            self.error = "API key or location not configured"
            return
        
        self.loading = True
        self.error = None
        
        try:
            # Current weather
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?q={self.location}&appid={self.api_key}&units=metric")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                self.weather_data = response.json()
                self.last_update = datetime.now()
            else:
                self.error = f"API error: {response.status_code}"
            
            # Forecast
            url = (f"https://api.openweathermap.org/data/2.5/forecast"
                   f"?q={self.location}&appid={self.api_key}&units=metric&cnt=8")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.forecast = data.get('list', [])[:5]
        
        except requests.exceptions.RequestException as e:
            self.error = f"Network error"
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.char == 'r' or event.char == 'R':
            self._fetch_weather()
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        return False
    
    def _get_weather_icon(self, code: str) -> str:
        """Get weather icon from code."""
        icons = {
            '01d': '☀', '01n': '🌙',
            '02d': '⛅', '02n': '☁',
            '03d': '☁', '03n': '☁',
            '04d': '☁', '04n': '☁',
            '09d': '🌧', '09n': '🌧',
            '10d': '🌦', '10n': '🌧',
            '11d': '⛈', '11n': '⛈',
            '13d': '❄', '13n': '❄',
            '50d': '🌫', '50n': '🌫',
        }
        return icons.get(code, '?')
    
    def draw(self, display: Display):
        """Draw weather screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a1628')
        
        if self.loading:
            display.text(display.width // 2, display.height // 2,
                        'Loading...', 'white', 16, 'mm')
            return
        
        if self.error:
            display.text(display.width // 2, display.height // 2 - 20,
                        'Error', '#ff4444', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        self.error[:30], '#888888', 12, 'mm')
            display.text(display.width // 2, display.height // 2 + 35,
                        'R: Retry', '#666666', 12, 'mm')
            return
        
        if not self.weather_data:
            display.text(display.width // 2, display.height // 2 - 10,
                        'No weather data', '#888888', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        'Configure API key in settings', '#666666', 11, 'mm')
            return
        
        # Current weather
        self._draw_current(display)
        
        # Forecast
        if self.forecast:
            self._draw_forecast(display)
    
    def _draw_current(self, display: Display):
        """Draw current weather."""
        data = self.weather_data
        
        # Location
        city = data.get('name', 'Unknown')
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 8, city, 'white', 14)
        
        # Last update
        if self.last_update:
            time_str = self.last_update.strftime('%H:%M')
            display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 8,
                        time_str, '#666666', 11, 'rt')
        
        # Main weather
        main = data.get('main', {})
        weather = data.get('weather', [{}])[0]
        
        temp = main.get('temp', 0)
        desc = weather.get('description', '').title()
        icon_code = weather.get('icon', '01d')
        
        # Large temperature
        temp_str = f"{temp:.0f}°"
        display.text(60, self.ui.STATUS_BAR_HEIGHT + 70, temp_str, 'white', 40, 'mm')
        
        # Weather icon
        icon = self._get_weather_icon(icon_code)
        display.text(display.width - 50, self.ui.STATUS_BAR_HEIGHT + 60, 
                    icon, 'white', 36, 'mm')
        
        # Description
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 105,
                    desc, '#aaaaaa', 14, 'mm')
        
        # Details
        details_y = self.ui.STATUS_BAR_HEIGHT + 130
        
        # Feels like
        feels = main.get('feels_like', temp)
        display.text(10, details_y, f"Feels: {feels:.0f}°", '#888888', 12)
        
        # Humidity
        humidity = main.get('humidity', 0)
        display.text(display.width // 2, details_y, f"💧 {humidity}%", '#888888', 12, 'mt')
        
        # Wind
        wind = data.get('wind', {}).get('speed', 0)
        display.text(display.width - 10, details_y, f"💨 {wind:.1f}m/s", '#888888', 12, 'rt')
        
        # High/Low
        high = main.get('temp_max', temp)
        low = main.get('temp_min', temp)
        display.text(display.width // 2, details_y + 18,
                    f"H: {high:.0f}° L: {low:.0f}°", '#666666', 11, 'mt')
    
    def _draw_forecast(self, display: Display):
        """Draw forecast."""
        start_y = self.ui.STATUS_BAR_HEIGHT + 175
        
        display.line(10, start_y - 5, display.width - 10, start_y - 5, '#333333')
        
        col_width = display.width // len(self.forecast)
        
        for i, item in enumerate(self.forecast):
            x = i * col_width + col_width // 2
            
            # Time
            dt = datetime.fromtimestamp(item.get('dt', 0))
            time_str = dt.strftime('%H:%M')
            display.text(x, start_y + 5, time_str, '#666666', 10, 'mt')
            
            # Icon
            weather = item.get('weather', [{}])[0]
            icon_code = weather.get('icon', '01d')
            icon = self._get_weather_icon(icon_code)
            display.text(x, start_y + 25, icon, 'white', 18, 'mm')
            
            # Temp
            temp = item.get('main', {}).get('temp', 0)
            display.text(x, start_y + 45, f"{temp:.0f}°", 'white', 12, 'mt')

