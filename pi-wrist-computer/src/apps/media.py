"""
Media Browser Application

Browse and view media files:
- Images (jpg, png, gif)
- Music (mp3, wav, ogg)
- Videos (mp4 - limited on Pi Zero)
- Documents (txt, pdf preview)
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from PIL import Image
import os
import subprocess
import threading


class MediaApp(App):
    """Media browser and player."""
    
    SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    SUPPORTED_AUDIO = ['.mp3', '.wav', '.ogg', '.flac']
    SUPPORTED_VIDEO = ['.mp4', '.avi', '.mkv']
    SUPPORTED_DOCS = ['.txt', '.md', '.pdf']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='media',
            name='Media',
            icon='🎬',
            color='#ff69b4'
        )
        
        # File browser state
        self.current_path = os.path.expanduser('~')
        self.files = []
        self.selected_index = 0
        self.scroll_offset = 0
        
        # View state
        self.mode = 'browse'  # 'browse', 'image', 'audio', 'video', 'doc'
        
        # Current media
        self.current_image = None
        self.current_doc_lines = []
        self.doc_scroll = 0
        
        # Audio state
        self.audio_playing = False
        self.audio_process = None
        self.audio_file = ""
        
        # Image zoom/pan
        self.image_zoom = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
    
    def on_enter(self):
        """Load current directory."""
        self._load_directory()
        self.mode = 'browse'
    
    def on_exit(self):
        """Stop any playing media."""
        self._stop_audio()
    
    def _load_directory(self):
        """Load files from current directory."""
        self.files = []
        self.selected_index = 0
        self.scroll_offset = 0
        
        try:
            # Add parent directory
            if self.current_path != '/':
                self.files.append({'name': '..', 'type': 'dir', 'path': os.path.dirname(self.current_path)})
            
            # List directory contents
            items = sorted(os.listdir(self.current_path))
            
            # Directories first
            for item in items:
                if item.startswith('.'):
                    continue
                full_path = os.path.join(self.current_path, item)
                if os.path.isdir(full_path):
                    self.files.append({'name': item, 'type': 'dir', 'path': full_path})
            
            # Then files
            for item in items:
                if item.startswith('.'):
                    continue
                full_path = os.path.join(self.current_path, item)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(item)[1].lower()
                    file_type = self._get_file_type(ext)
                    if file_type:
                        self.files.append({
                            'name': item, 
                            'type': file_type, 
                            'path': full_path,
                            'ext': ext
                        })
        except PermissionError:
            self.files = [{'name': '.. (access denied)', 'type': 'dir', 'path': os.path.dirname(self.current_path)}]
    
    def _get_file_type(self, ext: str) -> str:
        """Get file type from extension."""
        if ext in self.SUPPORTED_IMAGES:
            return 'image'
        elif ext in self.SUPPORTED_AUDIO:
            return 'audio'
        elif ext in self.SUPPORTED_VIDEO:
            return 'video'
        elif ext in self.SUPPORTED_DOCS:
            return 'doc'
        return None
    
    def _get_icon(self, file_type: str) -> str:
        """Get icon for file type."""
        icons = {
            'dir': '📁',
            'image': '🖼',
            'audio': '🎵',
            'video': '🎬',
            'doc': '📄'
        }
        return icons.get(file_type, '📄')
    
    def _open_file(self, file_info: dict):
        """Open selected file."""
        if file_info['type'] == 'dir':
            self.current_path = file_info['path']
            self._load_directory()
        elif file_info['type'] == 'image':
            self._open_image(file_info['path'])
        elif file_info['type'] == 'audio':
            self._play_audio(file_info['path'])
        elif file_info['type'] == 'video':
            self._play_video(file_info['path'])
        elif file_info['type'] == 'doc':
            self._open_doc(file_info['path'])
    
    def _open_image(self, path: str):
        """Open and display image."""
        try:
            img = Image.open(path)
            # Resize to fit screen
            img.thumbnail((self.ui.display.width, self.ui.display.height - 40))
            self.current_image = img.convert('RGB')
            self.image_zoom = 1.0
            self.image_offset_x = 0
            self.image_offset_y = 0
            self.mode = 'image'
        except Exception as e:
            print(f"Error opening image: {e}")
    
    def _play_audio(self, path: str):
        """Play audio file."""
        self._stop_audio()
        self.audio_file = os.path.basename(path)
        self.mode = 'audio'
        
        # Use mpv or aplay for playback
        try:
            self.audio_process = subprocess.Popen(
                ['mpv', '--no-video', path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.audio_playing = True
        except FileNotFoundError:
            try:
                # Fallback to aplay for wav
                self.audio_process = subprocess.Popen(
                    ['aplay', path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.audio_playing = True
            except:
                self.audio_playing = False
    
    def _stop_audio(self):
        """Stop audio playback."""
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None
        self.audio_playing = False
    
    def _play_video(self, path: str):
        """Play video file (uses external player)."""
        self.mode = 'video'
        # Use omxplayer or mpv for Pi
        try:
            subprocess.Popen(
                ['mpv', '--fs', path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass
    
    def _open_doc(self, path: str):
        """Open document."""
        self.current_doc_lines = []
        self.doc_scroll = 0
        
        try:
            ext = os.path.splitext(path)[1].lower()
            
            if ext in ['.txt', '.md']:
                with open(path, 'r', errors='ignore') as f:
                    text = f.read()
                    self.current_doc_lines = text.split('\n')
            elif ext == '.pdf':
                # Try to extract text from PDF
                try:
                    result = subprocess.run(
                        ['pdftotext', '-layout', path, '-'],
                        capture_output=True, text=True, timeout=10
                    )
                    self.current_doc_lines = result.stdout.split('\n')
                except:
                    self.current_doc_lines = ['PDF preview not available', 'Install poppler-utils']
            
            self.mode = 'doc'
        except Exception as e:
            self.current_doc_lines = [f'Error: {str(e)}']
            self.mode = 'doc'
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'browse':
            return self._handle_browse_key(event)
        elif self.mode == 'image':
            return self._handle_image_key(event)
        elif self.mode == 'audio':
            return self._handle_audio_key(event)
        elif self.mode == 'doc':
            return self._handle_doc_key(event)
        elif self.mode == 'video':
            if event.code == KeyCode.ESC:
                self.mode = 'browse'
            return True
        return False
    
    def _handle_browse_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.files:
                self._open_file(self.files[self.selected_index])
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            if self.current_path != '/':
                self.current_path = os.path.dirname(self.current_path)
                self._load_directory()
            else:
                self.ui.go_home()
            return True
        elif event.char == 'h' or event.char == 'H':
            self.current_path = os.path.expanduser('~')
            self._load_directory()
            return True
        return False
    
    def _handle_image_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'browse'
            self.current_image = None
            return True
        elif event.code == KeyCode.UP:
            self.image_offset_y += 20
            return True
        elif event.code == KeyCode.DOWN:
            self.image_offset_y -= 20
            return True
        elif event.code == KeyCode.LEFT:
            self.image_offset_x += 20
            return True
        elif event.code == KeyCode.RIGHT:
            self.image_offset_x -= 20
            return True
        elif event.char == '+' or event.char == '=':
            self.image_zoom = min(4.0, self.image_zoom + 0.25)
            return True
        elif event.char == '-':
            self.image_zoom = max(0.25, self.image_zoom - 0.25)
            return True
        return False
    
    def _handle_audio_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self._stop_audio()
            self.mode = 'browse'
            return True
        elif event.code == KeyCode.SPACE or event.code == KeyCode.ENTER:
            if self.audio_playing:
                self._stop_audio()
            return True
        return False
    
    def _handle_doc_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'browse'
            return True
        elif event.code == KeyCode.UP:
            if self.doc_scroll > 0:
                self.doc_scroll -= 1
            return True
        elif event.code == KeyCode.DOWN:
            self.doc_scroll += 1
            return True
        elif event.code == KeyCode.PAGEUP:
            self.doc_scroll = max(0, self.doc_scroll - 10)
            return True
        elif event.code == KeyCode.PAGEDOWN:
            self.doc_scroll += 10
            return True
        return False
    
    def draw(self, display: Display):
        """Draw media browser."""
        if self.mode == 'browse':
            self._draw_browser(display)
        elif self.mode == 'image':
            self._draw_image(display)
        elif self.mode == 'audio':
            self._draw_audio(display)
        elif self.mode == 'doc':
            self._draw_doc(display)
        elif self.mode == 'video':
            self._draw_video(display)
    
    def _draw_browser(self, display: Display):
        """Draw file browser."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        # Path bar
        path_display = self.current_path
        if len(path_display) > 30:
            path_display = '...' + path_display[-27:]
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, path_display, '#888888', 10)
        
        # File list
        item_height = 28
        start_y = self.ui.STATUS_BAR_HEIGHT + 25
        max_visible = (display.height - start_y - 5) // item_height
        
        # Adjust scroll
        if self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
        
        for i in range(max_visible):
            idx = self.scroll_offset + i
            if idx >= len(self.files):
                break
            
            file_info = self.files[idx]
            y = start_y + i * item_height
            selected = (idx == self.selected_index)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2, fill='#0066cc')
            
            # Icon
            icon = self._get_icon(file_info['type'])
            display.text(10, y + item_height // 2 - 2, icon, 'white', 14, 'lm')
            
            # Name
            name = file_info['name'][:28]
            display.text(35, y + item_height // 2 - 2, name, 
                        'white' if selected else '#cccccc', 11, 'lm')
    
    def _draw_image(self, display: Display):
        """Draw image viewer."""
        display.clear('black')
        
        if self.current_image:
            # Apply zoom
            if self.image_zoom != 1.0:
                new_size = (
                    int(self.current_image.width * self.image_zoom),
                    int(self.current_image.height * self.image_zoom)
                )
                img = self.current_image.resize(new_size, Image.LANCZOS)
            else:
                img = self.current_image
            
            # Calculate position (centered with offset)
            x = (display.width - img.width) // 2 + self.image_offset_x
            y = (display.height - img.height) // 2 + self.image_offset_y
            
            display.image(x, y, img)
        
        # Controls hint
        display.rect(0, display.height - 20, display.width, 20, fill='#000000aa')
        display.text(display.width // 2, display.height - 10,
                    'ESC:Back +/-:Zoom Arrows:Pan', '#888888', 9, 'mm')
    
    def _draw_audio(self, display: Display):
        """Draw audio player."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        # Music icon
        display.text(display.width // 2, display.height // 2 - 40, '🎵', 'white', 48, 'mm')
        
        # Filename
        name = self.audio_file[:30]
        display.text(display.width // 2, display.height // 2 + 20, name, 'white', 12, 'mm')
        
        # Status
        status = 'Playing...' if self.audio_playing else 'Stopped'
        display.text(display.width // 2, display.height // 2 + 45, status, '#888888', 11, 'mm')
        
        # Controls
        display.text(display.width // 2, display.height - 30,
                    'Space: Stop | ESC: Back', '#666666', 10, 'mm')
    
    def _draw_video(self, display: Display):
        """Draw video placeholder."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        display.text(display.width // 2, display.height // 2,
                    'Video playing externally', '#888888', 12, 'mm')
        display.text(display.width // 2, display.height // 2 + 20,
                    'ESC to return', '#666666', 11, 'mm')
    
    def _draw_doc(self, display: Display):
        """Draw document viewer."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        # Content
        line_height = 14
        start_y = self.ui.STATUS_BAR_HEIGHT + 10
        max_lines = (display.height - start_y - 20) // line_height
        
        visible = self.current_doc_lines[self.doc_scroll:self.doc_scroll + max_lines]
        
        for i, line in enumerate(visible):
            y = start_y + i * line_height
            display.text(5, y, line[:42], 'white', 10)
        
        # Scroll indicator
        if len(self.current_doc_lines) > max_lines:
            display.text(display.width - 10, display.height - 15,
                        f'{self.doc_scroll + 1}/{len(self.current_doc_lines)}', 
                        '#666666', 9, 'rm')

