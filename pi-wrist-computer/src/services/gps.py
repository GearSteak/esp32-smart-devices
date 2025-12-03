"""
GPS Service

Interfaces with gpsd for GPS data.
"""

import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable
import math


@dataclass
class GPSData:
    """GPS position data."""
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    speed: float = 0.0  # m/s
    heading: float = 0.0  # degrees
    fix: int = 0  # 0=no fix, 2=2D, 3=3D
    satellites: int = 0
    timestamp: float = 0.0
    
    @property
    def speed_kmh(self) -> float:
        return self.speed * 3.6
    
    @property
    def speed_mph(self) -> float:
        return self.speed * 2.237
    
    def distance_to(self, lat: float, lon: float) -> float:
        """Calculate distance to another point in meters (Haversine)."""
        R = 6371000  # Earth radius in meters
        
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(lat)
        dlat = math.radians(lat - self.latitude)
        dlon = math.radians(lon - self.longitude)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def bearing_to(self, lat: float, lon: float) -> float:
        """Calculate bearing to another point in degrees."""
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(lat)
        dlon = math.radians(lon - self.longitude)
        
        x = math.sin(dlon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) - 
             math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360


class GPSService:
    """GPS service using gpsd."""
    
    def __init__(self, config: dict):
        """
        Initialize GPS service.
        
        Args:
            config: GPS configuration with:
                - enabled: bool
                - device: serial device path
                - baudrate: serial baud rate
        """
        self.enabled = config.get('enabled', True)
        self.device = config.get('device', '/dev/ttyAMA0')
        
        self._data = GPSData()
        self._running = False
        self._thread = None
        self._callbacks = []
        self._gpsd = None
    
    def start(self):
        """Start GPS service."""
        if not self.enabled:
            return
        
        try:
            import gpsd
            gpsd.connect()
            self._gpsd = gpsd
            
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            print(f"GPS: Failed to connect to gpsd: {e}")
            self.enabled = False
    
    def stop(self):
        """Stop GPS service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _poll_loop(self):
        """Background polling loop."""
        while self._running:
            try:
                packet = self._gpsd.get_current()
                
                self._data.timestamp = time.time()
                self._data.fix = packet.mode
                
                if packet.mode >= 2:
                    self._data.latitude = packet.lat
                    self._data.longitude = packet.lon
                    self._data.speed = packet.hspeed if hasattr(packet, 'hspeed') else 0
                    self._data.heading = packet.track if hasattr(packet, 'track') else 0
                    
                    if packet.mode >= 3:
                        self._data.altitude = packet.alt if hasattr(packet, 'alt') else 0
                    
                    if hasattr(packet, 'sats'):
                        self._data.satellites = packet.sats
                
                # Notify callbacks
                for cb in self._callbacks:
                    try:
                        cb(self._data)
                    except Exception as e:
                        print(f"GPS callback error: {e}")
            
            except Exception as e:
                # gpsd connection issues
                pass
            
            time.sleep(1)
    
    def on_update(self, callback: Callable[[GPSData], None]):
        """Register callback for GPS updates."""
        self._callbacks.append(callback)
    
    def get_data(self) -> GPSData:
        """Get current GPS data."""
        return self._data
    
    @property
    def has_fix(self) -> bool:
        """Check if GPS has a fix."""
        return self._data.fix >= 2
    
    @property
    def position(self) -> tuple:
        """Get current position as (lat, lon)."""
        return (self._data.latitude, self._data.longitude)

