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
from src.input.usb_joystick import USBJoystick
from src.input.ble_joystick import BLEJoystick
from src.input.hid_joystick import HIDJoystick
from src.services.gps import GPSService
from src.services.battery import BatteryService

# Import apps
from src.apps.home import HomeApp
from src.apps.settings import SettingsApp
from src.apps.notes import NotesApp
from src.apps.calendar_app import CalendarApp
from src.apps.calculator import CalculatorApp
from src.apps.weather import WeatherApp
from src.apps.clock import ClockApp
from src.apps.games.tetris import TetrisApp
from src.apps.games.snake import SnakeApp
from src.apps.games.game_2048 import Game2048App
from src.apps.games.solitaire import SolitaireApp
from src.apps.games.minesweeper import MinesweeperApp
from src.apps.games.pong import PongApp
from src.apps.games.breakout import BreakoutApp
from src.apps.games.wordle import WordleApp
from src.apps.games.flappy import FlappyApp
from src.apps.games.connect4 import Connect4App
from src.apps.games.simon import SimonApp
from src.apps.games.hangman import HangmanApp
from src.apps.games.puzzle15 import Puzzle15App
from src.apps.games.memory import MemoryApp
from src.apps.games.rps import RPSApp
from src.apps.games.tictactoe import TicTacToeApp
from src.apps.games.blackjack import BlackjackApp
from src.apps.games.invaders import InvadersApp
from src.apps.games.asteroids import AsteroidsApp
from src.apps.games.checkers import CheckersApp
from src.apps.games.chess import ChessApp
from src.apps.games.uno import UnoApp
from src.apps.games.pinball import PinballApp
from src.apps.games.gamewatch import GameWatchApp
from src.apps.navigation import NavigationApp
from src.apps.lockscreen import LockScreen
from src.apps.email_client import EmailApp
from src.apps.browser import BrowserApp
from src.apps.media import MediaApp
from src.apps.dice import DiceApp
from src.apps.ttrpg import TTRPGApp
from src.apps.light_tracker import LightTrackerApp
from src.apps.passwords import PasswordsApp
from src.apps.spotify import SpotifyApp
from src.apps.notifications import NotificationsApp


class PiWristComputer:
    """Main application class."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize the wrist computer."""
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Check GPIO availability first and force cleanup any previous state
        from src.utils.gpio_manager import gpio
        if not gpio.available:
            print("WARNING: GPIO not available. Display may not work correctly.")
            print("Make sure you're running on a Raspberry Pi with RPi.GPIO installed.")
        else:
            # Force cleanup any previous GPIO state (in case previous run didn't exit cleanly)
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except:
                pass
            
            # Try to initialize GPIO early
            if not gpio.initialize():
                print("WARNING: GPIO initialization failed. Display may not work correctly.")
        
        # Initialize hardware
        print("Initializing display...")
        self.display = Display(self.config.get('display', {}))
        
        print("Initializing CardKB...")
        self.cardkb = CardKB(self.config.get('input', {}).get('cardkb', {}))
        
        print("Initializing trackball...")
        self.trackball = Trackball(self.config.get('input', {}).get('trackball', {}))
        
        print("Initializing USB joystick (ESP32 controller)...")
        self.usb_joystick = USBJoystick(self.config.get('input', {}).get('usb_joystick', {}))
        
        print("Initializing BLE joystick (ESP32 controller)...")
        self.ble_joystick = BLEJoystick(self.config.get('input', {}).get('ble_joystick', {}))
        
        print("Initializing HID joystick (Arduino Pro Micro)...")
        self.hid_joystick = HIDJoystick(self.config.get('input', {}).get('hid_joystick', {}))
        
        # Initialize UI
        print("Initializing UI framework...")
        ui_config = self.config.get('ui', {})
        # Pass battery visibility from battery config
        battery_config = self.config.get('battery', {})
        ui_config['show_battery'] = battery_config.get('show_indicator', True)
        
        # Choose joystick: HID > BLE > USB
        if self.hid_joystick.enabled:
            joystick = self.hid_joystick
        elif self.ble_joystick.enabled:
            joystick = self.ble_joystick
        else:
            joystick = self.usb_joystick
        
        self.ui = UI(
            self.display, 
            self.cardkb, 
            self.trackball,
            joystick,
            ui_config
        )
        
        # Add HID joystick to UI if enabled
        if self.hid_joystick.enabled:
            self.ui.hid_joystick = self.hid_joystick
            self.hid_joystick.on_move(self.ui._on_cursor_move)
            self.hid_joystick.on_click(self.ui._on_click)
            self.hid_joystick.on_key(self.ui._on_key)
        
        # Initialize services
        print("Initializing GPS...")
        self.gps = GPSService(self.config.get('gps', {}))
        
        print("Initializing battery monitor...")
        self.battery = BatteryService(self.config.get('battery', {}))
        
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
        self.ui.register_app(ClockApp(self.ui))
        
        # Games
        self.ui.register_app(TetrisApp(self.ui))
        self.ui.register_app(SnakeApp(self.ui))
        self.ui.register_app(Game2048App(self.ui))
        self.ui.register_app(SolitaireApp(self.ui))
        self.ui.register_app(MinesweeperApp(self.ui))
        self.ui.register_app(PongApp(self.ui))
        self.ui.register_app(BreakoutApp(self.ui))
        self.ui.register_app(WordleApp(self.ui))
        self.ui.register_app(FlappyApp(self.ui))
        self.ui.register_app(Connect4App(self.ui))
        self.ui.register_app(SimonApp(self.ui))
        self.ui.register_app(HangmanApp(self.ui))
        self.ui.register_app(Puzzle15App(self.ui))
        self.ui.register_app(MemoryApp(self.ui))
        self.ui.register_app(RPSApp(self.ui))
        self.ui.register_app(TicTacToeApp(self.ui))
        self.ui.register_app(BlackjackApp(self.ui))
        self.ui.register_app(InvadersApp(self.ui))
        self.ui.register_app(AsteroidsApp(self.ui))
        self.ui.register_app(CheckersApp(self.ui))
        self.ui.register_app(ChessApp(self.ui))
        self.ui.register_app(UnoApp(self.ui))
        self.ui.register_app(PinballApp(self.ui))
        self.ui.register_app(GameWatchApp(self.ui))
        
        # Navigation (with GPS service)
        nav_app = NavigationApp(self.ui, self.gps)
        self.ui.register_app(nav_app)
        
        # Lock screen
        self.lock_screen = LockScreen(self.ui)
        self.ui.register_app(self.lock_screen)
        
        # Email client
        self.ui.register_app(EmailApp(self.ui))
        
        # Web browser
        self.ui.register_app(BrowserApp(self.ui))
        
        # Media browser
        self.ui.register_app(MediaApp(self.ui))
        
        # TTRPG apps
        self.ui.register_app(DiceApp(self.ui))
        self.ui.register_app(TTRPGApp(self.ui))
        self.ui.register_app(LightTrackerApp(self.ui))
        
        # Password vault
        self.ui.register_app(PasswordsApp(self.ui))
        
        # Spotify
        self.ui.register_app(SpotifyApp(self.ui))
        
        # Notifications (iOS ANCS)
        self.ui.register_app(NotificationsApp(self.ui))
    
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
        
        # Check screen timeout (only on home screen)
        if (self.ui.current_app and 
            self.ui.current_app.info.id == 'home' and
            self.lock_screen.check_timeout()):
            self.lock_screen.lock()
            self.lock_screen.sleep_screen()
    
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

