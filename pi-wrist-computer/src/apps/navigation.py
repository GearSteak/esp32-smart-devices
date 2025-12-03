"""
Navigation Application

GPS navigation with:
- Compass arrow to destination
- Speed display
- Distance/ETA
- Basic waypoint navigation
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from ..services.gps import GPSService, GPSData
import math
import json
import os


class NavigationApp(App):
    """GPS Navigation application."""
    
    def __init__(self, ui, gps_service: GPSService = None):
        super().__init__(ui)
        self.info = AppInfo(
            id='navigation',
            name='Navigate',
            icon='🧭',
            color='#00aaff'
        )
        
        self.gps = gps_service
        self.gps_data = GPSData()
        
        # Waypoints
        self.waypoints = []
        self.current_waypoint = None
        self.waypoint_index = 0
        
        # Display mode
        self.mode = 'compass'  # 'compass', 'speed', 'waypoints'
        
        # Compass animation
        self._compass_angle = 0
        self._target_angle = 0
    
    def on_enter(self):
        """Start navigation."""
        if self.gps:
            self.gps.on_update(self._on_gps_update)
        self._load_waypoints()
    
    def on_exit(self):
        pass
    
    def _on_gps_update(self, data: GPSData):
        """Handle GPS update."""
        self.gps_data = data
        
        # Update compass angle to target
        if self.current_waypoint:
            self._target_angle = data.bearing_to(
                self.current_waypoint['lat'],
                self.current_waypoint['lon']
            )
    
    def _load_waypoints(self):
        """Load saved waypoints."""
        path = os.path.join(
            self.ui.config.get('paths', {}).get('calendar', './data'),
            'waypoints.json'
        )
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.waypoints = json.load(f)
        except Exception:
            self.waypoints = []
    
    def _save_waypoints(self):
        """Save waypoints to file."""
        path = os.path.join(
            self.ui.config.get('paths', {}).get('calendar', './data'),
            'waypoints.json'
        )
        try:
            with open(path, 'w') as f:
                json.dump(self.waypoints, f)
        except Exception as e:
            print(f"Error saving waypoints: {e}")
    
    def _add_current_location(self, name: str = None):
        """Save current location as waypoint."""
        if not self.gps_data.fix >= 2:
            return
        
        if not name:
            name = f"WP{len(self.waypoints) + 1}"
        
        self.waypoints.append({
            'name': name,
            'lat': self.gps_data.latitude,
            'lon': self.gps_data.longitude
        })
        self._save_waypoints()
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.LEFT:
            if self.mode == 'compass':
                self.mode = 'waypoints'
            elif self.mode == 'speed':
                self.mode = 'compass'
            elif self.mode == 'waypoints':
                self.mode = 'speed'
            return True
        elif event.code == KeyCode.RIGHT:
            if self.mode == 'compass':
                self.mode = 'speed'
            elif self.mode == 'speed':
                self.mode = 'waypoints'
            elif self.mode == 'waypoints':
                self.mode = 'compass'
            return True
        elif event.code == KeyCode.UP and self.mode == 'waypoints':
            if self.waypoint_index > 0:
                self.waypoint_index -= 1
            return True
        elif event.code == KeyCode.DOWN and self.mode == 'waypoints':
            if self.waypoint_index < len(self.waypoints) - 1:
                self.waypoint_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.mode == 'waypoints' and self.waypoints:
                self.current_waypoint = self.waypoints[self.waypoint_index]
                self.mode = 'compass'
            return True
        elif event.char == 's' or event.char == 'S':
            self._add_current_location()
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def update(self, dt: float):
        """Update compass animation."""
        # Smooth compass rotation
        diff = self._target_angle - self._compass_angle
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        
        self._compass_angle += diff * dt * 3
        self._compass_angle %= 360
    
    def draw(self, display: Display):
        """Draw navigation screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        if self.mode == 'compass':
            self._draw_compass(display)
        elif self.mode == 'speed':
            self._draw_speed(display)
        elif self.mode == 'waypoints':
            self._draw_waypoints(display)
        
        # Mode tabs
        self._draw_tabs(display)
    
    def _draw_tabs(self, display: Display):
        """Draw mode tabs at bottom."""
        y = display.height - 25
        tab_width = display.width // 3
        
        tabs = [
            ('compass', '🧭 Compass'),
            ('speed', '⚡ Speed'),
            ('waypoints', '📍 Points'),
        ]
        
        for i, (mode, label) in enumerate(tabs):
            x = i * tab_width
            selected = self.mode == mode
            
            if selected:
                display.rect(x, y, tab_width, 25, fill='#0066cc')
            
            display.text(x + tab_width // 2, y + 12, label,
                        'white' if selected else '#666666', 11, 'mm')
    
    def _draw_compass(self, display: Display):
        """Draw compass view."""
        cx = display.width // 2
        cy = self.ui.STATUS_BAR_HEIGHT + 100
        radius = 70
        
        # GPS status
        if self.gps_data.fix < 2:
            display.text(cx, self.ui.STATUS_BAR_HEIGHT + 15,
                        'Acquiring GPS...', '#ffcc00', 14, 'mm')
        else:
            sats = f"📡 {self.gps_data.satellites} sats"
            display.text(10, self.ui.STATUS_BAR_HEIGHT + 8, sats, '#888888', 11)
        
        # Compass circle
        display.circle(cx, cy, radius, color='#333333', width=2)
        display.circle(cx, cy, radius - 5, color='#222222')
        
        # Cardinal directions
        directions = [('N', 0), ('E', 90), ('S', 180), ('W', 270)]
        for label, angle in directions:
            rad = math.radians(angle - self._compass_angle - 90)
            x = cx + int((radius - 15) * math.cos(rad))
            y = cy + int((radius - 15) * math.sin(rad))
            color = '#ff4444' if label == 'N' else '#888888'
            display.text(x, y, label, color, 14, 'mm')
        
        # Bearing arrow (if target set)
        if self.current_waypoint:
            bearing = self.gps_data.bearing_to(
                self.current_waypoint['lat'],
                self.current_waypoint['lon']
            )
            rel_bearing = bearing - self._compass_angle
            rad = math.radians(rel_bearing - 90)
            
            # Arrow
            arrow_len = radius - 25
            ax = cx + int(arrow_len * math.cos(rad))
            ay = cy + int(arrow_len * math.sin(rad))
            
            # Arrow head
            display.line(cx, cy, ax, ay, '#00ff00', 3)
            
            # Distance
            dist = self.gps_data.distance_to(
                self.current_waypoint['lat'],
                self.current_waypoint['lon']
            )
            
            if dist >= 1000:
                dist_str = f"{dist/1000:.1f} km"
            else:
                dist_str = f"{int(dist)} m"
            
            display.text(cx, cy + radius + 25, dist_str, '#00ff00', 18, 'mm')
            display.text(cx, cy + radius + 45, 
                        self.current_waypoint['name'], '#888888', 12, 'mm')
        else:
            # Current heading
            display.text(cx, cy, f"{int(self._compass_angle)}°", 'white', 24, 'mm')
        
        # Speed at bottom
        speed_kmh = self.gps_data.speed_kmh
        display.text(cx, cy + radius + 70, f"{speed_kmh:.1f} km/h", 
                    'white', 14, 'mm')
    
    def _draw_speed(self, display: Display):
        """Draw speedometer view."""
        cx = display.width // 2
        cy = self.ui.STATUS_BAR_HEIGHT + 80
        
        # GPS status
        if self.gps_data.fix < 2:
            display.text(cx, cy, 'No GPS Fix', '#ff4444', 18, 'mm')
            return
        
        # Large speed display
        speed_kmh = self.gps_data.speed_kmh
        display.text(cx, cy, f"{speed_kmh:.0f}", 'white', 48, 'mm')
        display.text(cx, cy + 35, 'km/h', '#888888', 16, 'mm')
        
        # Altitude
        if self.gps_data.fix >= 3:
            alt = f"↑ {self.gps_data.altitude:.0f} m"
            display.text(cx, cy + 65, alt, '#888888', 14, 'mm')
        
        # Heading
        heading = f"→ {self.gps_data.heading:.0f}°"
        display.text(cx, cy + 85, heading, '#888888', 14, 'mm')
        
        # Coordinates
        lat = self.gps_data.latitude
        lon = self.gps_data.longitude
        display.text(cx, cy + 115, f"{lat:.5f}, {lon:.5f}", '#666666', 11, 'mm')
    
    def _draw_waypoints(self, display: Display):
        """Draw waypoints list."""
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 8, 'Waypoints', 'white', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 8,
                    'S: Save Current', '#666666', 10, 'rt')
        
        if not self.waypoints:
            display.text(display.width // 2, display.height // 2 - 30,
                        'No waypoints saved', '#666666', 14, 'mm')
            display.text(display.width // 2, display.height // 2 - 10,
                        'Press S to save current location', '#666666', 12, 'mm')
            return
        
        # List waypoints
        item_height = 40
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        max_visible = (display.height - start_y - 30) // item_height
        
        for i, wp in enumerate(self.waypoints[:max_visible]):
            y = start_y + i * item_height
            selected = (i == self.waypoint_index)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2,
                            fill='#0066cc')
            
            # Name
            display.text(15, y + 10, wp['name'], 'white', 14)
            
            # Distance if GPS fix
            if self.gps_data.fix >= 2:
                dist = self.gps_data.distance_to(wp['lat'], wp['lon'])
                if dist >= 1000:
                    dist_str = f"{dist/1000:.1f} km"
                else:
                    dist_str = f"{int(dist)} m"
                
                display.text(display.width - 15, y + 10, dist_str,
                            '#888888', 12, 'rt')
            
            # Coordinates
            display.text(15, y + 26, f"{wp['lat']:.5f}, {wp['lon']:.5f}",
                        '#666666', 10)

