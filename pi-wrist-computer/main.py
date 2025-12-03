#!/usr/bin/env python3
"""
Pi Wrist Computer - Main Entry Point

Standalone wearable computer with:
- ST7789V 240x320 LCD display
- CardKB I2C keyboard
- 303trackba1 digital trackball
- GPS navigation
- WiFi/BLE connectivity
"""

import yaml
import time
import signal
import sys
from datetime import datetime

# Import components
from src.ui.display import Display
from src.ui.framework import UI, Notification
from src.input.cardkb import CardKB
from src.input.trackball import Trackball
from src.services.gps import GPSService
from src.services.battery import BatteryService

# Import apps
from src.apps.home import HomeApp
from src.apps.settings import SettingsApp
from src.apps.notes import NotesApp
from src.apps.calendar_app import CalendarApp
from src.apps.calculator import CalculatorApp
from src.apps.weather import WeatherApp
from src.apps.games.tetris import TetrisApp
from src.apps.games.snake import SnakeApp
from src.apps.games.game_2048 import Game2048App
from src.apps.games.solitaire import SolitaireApp
from src.apps.navigation import NavigationApp


class PiWristComputer:
    """Main application class."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize the wrist computer."""
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize hardware
        print("Initializing display...")
        self.display = Display(self.config.get('display', {}))
        
        print("Initializing CardKB...")
        self.cardkb = CardKB(self.config.get('input', {}).get('cardkb', {}))
        
        print("Initializing trackball...")
        self.trackball = Trackball(self.config.get('input', {}).get('trackball', {}))
        
        # Initialize UI
        print("Initializing UI framework...")
        self.ui = UI(
            self.display, 
            self.cardkb, 
            self.trackball,
            self.config.get('ui', {})
        )
        
        # Initialize services
        print("Initializing GPS...")
        self.gps = GPSService(self.config.get('gps', {}))
        
        print("Initializing battery monitor...")
        self.battery = BatteryService()
        
        # Register apps
        self._register_apps()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self._running = False
    
    def _load_config(self, path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file {path} not found, using defaults")
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _register_apps(self):
        """Register all applications."""
        # Core apps
        self.ui.register_app(HomeApp(self.ui))
        self.ui.register_app(SettingsApp(self.ui))
        self.ui.register_app(NotesApp(self.ui))
        self.ui.register_app(CalendarApp(self.ui))
        self.ui.register_app(CalculatorApp(self.ui))
        self.ui.register_app(WeatherApp(self.ui))
        
        # Games
        self.ui.register_app(TetrisApp(self.ui))
        self.ui.register_app(SnakeApp(self.ui))
        self.ui.register_app(Game2048App(self.ui))
        self.ui.register_app(SolitaireApp(self.ui))
        
        # Navigation (with GPS service)
        nav_app = NavigationApp(self.ui, self.gps)
        self.ui.register_app(nav_app)
        
        # TODO: Add more apps
        # - Email
        # - Browser
        # - Spotify
        # - Home Assistant
        # - Password vault
        # - Navigation
        # - ANCS notifications
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self._running = False
    
    def _update_status(self):
        """Update status bar information."""
        # Update time
        now = datetime.now()
        self.ui.set_status(time_str=now.strftime('%H:%M'))
        
        # Update battery
        self.ui.set_status(battery=self.battery.percent)
        
        # WiFi/BT status would be updated by respective services
    
    def run(self):
        """Main run loop."""
        print("Starting Pi Wrist Computer...")
        
        # Start services
        self.gps.start()
        self.battery.start()
        
        # Start on home screen
        self.ui.launch_app('home')
        
        self._running = True
        last_status_update = 0
        
        try:
            while self._running:
                # Update status every second
                now = time.time()
                if now - last_status_update >= 1:
                    self._update_status()
                    last_status_update = now
                
                # Update and draw UI
                self.ui.update()
                self.ui.draw()
                
                # Target ~30 FPS
                time.sleep(1/30)
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown."""
        print("Cleaning up...")
        
        # Stop services
        self.gps.stop()
        self.battery.stop()
        
        # Shutdown UI
        self.ui.shutdown()
        
        print("Goodbye!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pi Wrist Computer')
    parser.add_argument('-c', '--config', default='config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--demo', action='store_true',
                        help='Run in demo mode (simulated hardware)')
    args = parser.parse_args()
    
    if args.demo:
        print("Demo mode not yet implemented")
        print("Run on actual Pi hardware with connected peripherals")
        sys.exit(1)
    
    computer = PiWristComputer(args.config)
    computer.run()


if __name__ == '__main__':
    main()

