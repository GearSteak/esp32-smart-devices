"""
Spotify App
Control Spotify playback via Spotify Connect API.
"""

import os
import json
import time
from typing import Optional, Dict, List
from src.ui.display import Display
from src.input.keys import KeyEvent, KeyCode

# Try to import spotipy
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


class SpotifyApp:
    """
    Spotify Controller
    
    Controls Spotify playback on connected devices.
    Requires Spotify Premium for playback control.
    
    Setup:
    1. Create app at https://developer.spotify.com/dashboard
    2. Set redirect URI to http://localhost:8888/callback
    3. Add credentials to ~/spotify_credentials.json:
       {
         "client_id": "your_client_id",
         "client_secret": "your_client_secret"
       }
    """
    
    SCOPES = [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-library-read",
        "playlist-read-private",
    ]
    
    def __init__(self, ui):
        self.ui = ui
        self.sp: Optional[spotipy.Spotify] = None
        self.credentials_path = os.path.expanduser("~/spotify_credentials.json")
        self.cache_path = os.path.expanduser("~/.spotify_cache")
        
        self.mode = 'loading'  # loading, error, player, playlists, devices
        self.error_message = ""
        
        # Playback state
        self.is_playing = False
        self.current_track: Optional[Dict] = None
        self.current_artist = ""
        self.current_album = ""
        self.progress_ms = 0
        self.duration_ms = 0
        self.volume = 50
        self.shuffle = False
        self.repeat = 'off'  # off, track, context
        
        # Navigation state
        self.selected_index = 0
        self.scroll_offset = 0
        self.playlists: List[Dict] = []
        self.devices: List[Dict] = []
        self.active_device: Optional[str] = None
        
        # Refresh timing
        self.last_refresh = 0
        self.refresh_interval = 2.0
    
    def on_enter(self):
        """Called when app becomes active."""
        if not SPOTIPY_AVAILABLE:
            self.error_message = "spotipy not installed\npip install spotipy"
            self.mode = 'error'
            return
        
        if not os.path.exists(self.credentials_path):
            self.error_message = f"No credentials at\n{self.credentials_path}"
            self.mode = 'error'
            return
        
        self._init_spotify()
    
    def on_exit(self):
        """Called when leaving app."""
        pass
    
    def _init_spotify(self):
        """Initialize Spotify client."""
        try:
            with open(self.credentials_path, 'r') as f:
                creds = json.load(f)
            
            auth_manager = SpotifyOAuth(
                client_id=creds.get('client_id'),
                client_secret=creds.get('client_secret'),
                redirect_uri="http://localhost:8888/callback",
                scope=" ".join(self.SCOPES),
                cache_path=self.cache_path,
                open_browser=False
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Test connection
            self.sp.current_user()
            
            self.mode = 'player'
            self._refresh_playback()
            self._load_playlists()
            
        except Exception as e:
            self.error_message = f"Auth failed:\n{str(e)[:50]}"
            self.mode = 'error'
    
    def _refresh_playback(self):
        """Refresh current playback state."""
        if not self.sp:
            return
        
        try:
            playback = self.sp.current_playback()
            
            if playback:
                self.is_playing = playback.get('is_playing', False)
                self.progress_ms = playback.get('progress_ms', 0)
                self.volume = playback.get('device', {}).get('volume_percent', 50)
                self.shuffle = playback.get('shuffle_state', False)
                self.repeat = playback.get('repeat_state', 'off')
                self.active_device = playback.get('device', {}).get('id')
                
                track = playback.get('item')
                if track:
                    self.current_track = track
                    self.current_artist = ", ".join([a['name'] for a in track.get('artists', [])])
                    self.current_album = track.get('album', {}).get('name', '')
                    self.duration_ms = track.get('duration_ms', 0)
            else:
                self.is_playing = False
                self.current_track = None
            
            self.last_refresh = time.time()
            
        except Exception as e:
            print(f"Spotify refresh error: {e}")
    
    def _load_playlists(self):
        """Load user's playlists."""
        if not self.sp:
            return
        
        try:
            results = self.sp.current_user_playlists(limit=50)
            self.playlists = results.get('items', [])
        except Exception as e:
            print(f"Playlist load error: {e}")
    
    def _load_devices(self):
        """Load available devices."""
        if not self.sp:
            return
        
        try:
            results = self.sp.devices()
            self.devices = results.get('devices', [])
        except Exception as e:
            print(f"Device load error: {e}")
    
    def handle_input(self, event: KeyEvent) -> bool:
        """Handle input events."""
        if event.type != 'press':
            return False
        
        if self.mode == 'error':
            if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
                self.ui.go_back()
                return True
            return False
        
        if self.mode == 'player':
            return self._handle_player_input(event)
        elif self.mode == 'playlists':
            return self._handle_playlists_input(event)
        elif self.mode == 'devices':
            return self._handle_devices_input(event)
        
        return False
    
    def _handle_player_input(self, event: KeyEvent) -> bool:
        """Handle player screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.ui.go_back()
            return True
        
        if event.code == KeyCode.ENTER or event.char == ' ':
            # Play/Pause
            self._toggle_playback()
            return True
        elif event.code == KeyCode.LEFT:
            # Previous track
            self._previous_track()
            return True
        elif event.code == KeyCode.RIGHT:
            # Next track
            self._next_track()
            return True
        elif event.code == KeyCode.UP:
            # Volume up
            self._set_volume(min(100, self.volume + 10))
            return True
        elif event.code == KeyCode.DOWN:
            # Volume down
            self._set_volume(max(0, self.volume - 10))
            return True
        elif event.char == 'p' or event.char == 'P':
            # Show playlists
            self.mode = 'playlists'
            self.selected_index = 0
            self.scroll_offset = 0
            return True
        elif event.char == 'd' or event.char == 'D':
            # Show devices
            self._load_devices()
            self.mode = 'devices'
            self.selected_index = 0
            return True
        elif event.char == 's' or event.char == 'S':
            # Toggle shuffle
            self._toggle_shuffle()
            return True
        elif event.char == 'r' or event.char == 'R':
            # Toggle repeat
            self._toggle_repeat()
            return True
        
        return False
    
    def _handle_playlists_input(self, event: KeyEvent) -> bool:
        """Handle playlists screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'player'
            return True
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.playlists) - 1, self.selected_index + 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.ENTER:
            if self.playlists:
                self._play_playlist(self.playlists[self.selected_index])
                self.mode = 'player'
            return True
        
        return False
    
    def _handle_devices_input(self, event: KeyEvent) -> bool:
        """Handle devices screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'player'
            return True
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.devices) - 1, self.selected_index + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.devices:
                self._transfer_playback(self.devices[self.selected_index])
                self.mode = 'player'
            return True
        
        return False
    
    def _adjust_scroll(self):
        """Adjust scroll to keep selection visible."""
        max_visible = 8
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
    
    def _toggle_playback(self):
        """Toggle play/pause."""
        if not self.sp:
            return
        try:
            if self.is_playing:
                self.sp.pause_playback()
                self.is_playing = False
            else:
                self.sp.start_playback()
                self.is_playing = True
        except Exception as e:
            print(f"Playback toggle error: {e}")
    
    def _next_track(self):
        """Skip to next track."""
        if not self.sp:
            return
        try:
            self.sp.next_track()
            time.sleep(0.3)
            self._refresh_playback()
        except Exception as e:
            print(f"Next track error: {e}")
    
    def _previous_track(self):
        """Skip to previous track."""
        if not self.sp:
            return
        try:
            self.sp.previous_track()
            time.sleep(0.3)
            self._refresh_playback()
        except Exception as e:
            print(f"Previous track error: {e}")
    
    def _set_volume(self, volume: int):
        """Set playback volume."""
        if not self.sp:
            return
        try:
            self.sp.volume(volume)
            self.volume = volume
        except Exception as e:
            print(f"Volume error: {e}")
    
    def _toggle_shuffle(self):
        """Toggle shuffle mode."""
        if not self.sp:
            return
        try:
            self.sp.shuffle(not self.shuffle)
            self.shuffle = not self.shuffle
        except Exception as e:
            print(f"Shuffle error: {e}")
    
    def _toggle_repeat(self):
        """Cycle repeat mode."""
        if not self.sp:
            return
        try:
            modes = ['off', 'context', 'track']
            current_idx = modes.index(self.repeat) if self.repeat in modes else 0
            new_mode = modes[(current_idx + 1) % len(modes)]
            self.sp.repeat(new_mode)
            self.repeat = new_mode
        except Exception as e:
            print(f"Repeat error: {e}")
    
    def _play_playlist(self, playlist: Dict):
        """Start playing a playlist."""
        if not self.sp:
            return
        try:
            self.sp.start_playback(context_uri=playlist.get('uri'))
            time.sleep(0.5)
            self._refresh_playback()
        except Exception as e:
            print(f"Playlist play error: {e}")
    
    def _transfer_playback(self, device: Dict):
        """Transfer playback to device."""
        if not self.sp:
            return
        try:
            self.sp.transfer_playback(device.get('id'), force_play=True)
            self.active_device = device.get('id')
            time.sleep(0.5)
            self._refresh_playback()
        except Exception as e:
            print(f"Transfer error: {e}")
    
    def draw(self, display: Display):
        """Draw the Spotify interface."""
        # Auto-refresh playback state
        if self.mode == 'player' and time.time() - self.last_refresh > self.refresh_interval:
            self._refresh_playback()
        
        if self.mode == 'error':
            self._draw_error(display)
        elif self.mode == 'loading':
            self._draw_loading(display)
        elif self.mode == 'player':
            self._draw_player(display)
        elif self.mode == 'playlists':
            self._draw_playlists(display)
        elif self.mode == 'devices':
            self._draw_devices(display)
    
    def _draw_error(self, display: Display):
        """Draw error screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1db954')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🎵 SPOTIFY", 'white', 14, 'mm')
        
        display.text(display.width // 2, display.height // 2 - 20,
                    "Setup Required", '#ff6666', 14, 'mm')
        
        lines = self.error_message.split('\n')
        for i, line in enumerate(lines):
            display.text(display.width // 2, display.height // 2 + 10 + i * 18,
                        line, '#888888', 11, 'mm')
    
    def _draw_loading(self, display: Display):
        """Draw loading screen."""
        display.text(display.width // 2, display.height // 2,
                    "Connecting to Spotify...", '#1db954', 14, 'mm')
    
    def _draw_player(self, display: Display):
        """Draw player screen."""
        # Header
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1db954')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🎵 SPOTIFY", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        if not self.current_track:
            display.text(display.width // 2, display.height // 2,
                        "No track playing", '#888888', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 25,
                        "P: Playlists  D: Devices", '#666666', 10, 'mm')
            return
        
        # Track info
        track_name = self.current_track.get('name', 'Unknown')[:30]
        display.text(display.width // 2, content_y + 10, track_name, 'white', 16, 'mm')
        display.text(display.width // 2, content_y + 30, self.current_artist[:35], '#888888', 12, 'mm')
        display.text(display.width // 2, content_y + 48, self.current_album[:35], '#666666', 10, 'mm')
        
        # Progress bar
        bar_y = content_y + 70
        bar_width = display.width - 40
        display.rect(20, bar_y, bar_width, 6, fill='#333333')
        
        if self.duration_ms > 0:
            progress_pct = self.progress_ms / self.duration_ms
            display.rect(20, bar_y, int(bar_width * progress_pct), 6, fill='#1db954')
        
        # Time display
        progress_str = f"{self.progress_ms // 60000}:{(self.progress_ms // 1000) % 60:02d}"
        duration_str = f"{self.duration_ms // 60000}:{(self.duration_ms // 1000) % 60:02d}"
        display.text(20, bar_y + 12, progress_str, '#888888', 10, 'lt')
        display.text(display.width - 20, bar_y + 12, duration_str, '#888888', 10, 'rt')
        
        # Playback controls
        ctrl_y = bar_y + 35
        play_icon = "⏸" if self.is_playing else "▶"
        display.text(display.width // 2 - 50, ctrl_y, "⏮", 'white', 20, 'mm')
        display.text(display.width // 2, ctrl_y, play_icon, '#1db954', 24, 'mm')
        display.text(display.width // 2 + 50, ctrl_y, "⏭", 'white', 20, 'mm')
        
        # Volume
        vol_y = ctrl_y + 35
        display.text(15, vol_y, "🔊", 'white', 12)
        display.rect(40, vol_y - 3, 80, 6, fill='#333333')
        display.rect(40, vol_y - 3, int(80 * self.volume / 100), 6, fill='#1db954')
        display.text(130, vol_y, f"{self.volume}%", '#888888', 10, 'lm')
        
        # Shuffle/Repeat
        shuffle_color = '#1db954' if self.shuffle else '#666666'
        repeat_color = '#1db954' if self.repeat != 'off' else '#666666'
        repeat_icon = "🔂" if self.repeat == 'track' else "🔁"
        
        display.text(display.width - 60, vol_y, "🔀", shuffle_color, 14)
        display.text(display.width - 30, vol_y, repeat_icon, repeat_color, 14)
        
        # Help
        display.text(display.width // 2, display.height - 12,
                    "P:Playlists D:Devices S:Shuffle R:Repeat", '#555555', 9, 'mm')
    
    def _draw_playlists(self, display: Display):
        """Draw playlists screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1db954')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "📋 PLAYLISTS", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        if not self.playlists:
            display.text(display.width // 2, display.height // 2,
                        "No playlists found", '#888888', 14, 'mm')
            return
        
        max_visible = 8
        for i in range(max_visible):
            idx = self.scroll_offset + i
            if idx >= len(self.playlists):
                break
            
            playlist = self.playlists[idx]
            y = content_y + i * 25
            
            selected = (idx == self.selected_index)
            if selected:
                display.rect(0, y - 2, display.width, 23, fill='#1a3a1a')
            
            name = playlist.get('name', 'Untitled')[:30]
            tracks = playlist.get('tracks', {}).get('total', 0)
            
            display.text(10, y + 8, name, 'white' if selected else '#888888', 12)
            display.text(display.width - 10, y + 8, f"{tracks}", '#666666', 10, 'rm')
    
    def _draw_devices(self, display: Display):
        """Draw devices screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1db954')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "📱 DEVICES", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        if not self.devices:
            display.text(display.width // 2, display.height // 2,
                        "No devices found", '#888888', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 20,
                        "Open Spotify on a device", '#666666', 10, 'mm')
            return
        
        for i, device in enumerate(self.devices):
            y = content_y + i * 35
            
            selected = (i == self.selected_index)
            is_active = device.get('id') == self.active_device
            
            if selected:
                display.rect(0, y - 2, display.width, 33, fill='#1a3a1a')
            
            # Device type icon
            dtype = device.get('type', 'Unknown').lower()
            icon = "📱" if 'phone' in dtype else "💻" if 'computer' in dtype else "🔊"
            
            display.text(10, y + 12, icon, 'white', 16)
            display.text(40, y + 8, device.get('name', 'Unknown')[:25], 
                        '#1db954' if is_active else ('white' if selected else '#888888'), 12)
            display.text(40, y + 22, device.get('type', ''), '#666666', 9)
            
            if is_active:
                display.text(display.width - 10, y + 12, "●", '#1db954', 14, 'rm')

