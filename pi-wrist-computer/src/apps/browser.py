"""
Text-Mode Web Browser

Simple text-based web browser with:
- URL navigation
- HTML to text conversion
- Link navigation
- Bookmarks
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import requests
import json
import os
import re
from html.parser import HTMLParser


class HTMLToText(HTMLParser):
    """Convert HTML to plain text."""
    
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.in_script = False
        self.in_style = False
        self.in_link = False
        self.current_link = ""
    
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = True
        elif tag == 'style':
            self.in_style = True
        elif tag == 'a':
            self.in_link = True
            for attr, value in attrs:
                if attr == 'href':
                    self.current_link = value
        elif tag in ['p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'tr']:
            self.text.append('\n')
    
    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        elif tag == 'style':
            self.in_style = False
        elif tag == 'a':
            if self.in_link and self.current_link:
                link_idx = len(self.links)
                self.links.append(self.current_link)
                self.text.append(f' [{link_idx}]')
            self.in_link = False
            self.current_link = ""
        elif tag in ['p', 'div', 'h1', 'h2', 'h3', 'h4']:
            self.text.append('\n')
    
    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text.append(text + ' ')
    
    def get_text(self):
        return ''.join(self.text)
    
    def get_links(self):
        return self.links


class BrowserApp(App):
    """Text-mode web browser."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='browser',
            name='Browser',
            icon='🌐',
            color='#4dc9ff'
        )
        
        # State
        self.mode = 'home'  # 'home', 'browse', 'url_input', 'link_select'
        self.current_url = ""
        self.page_text = ""
        self.page_links = []
        self.scroll_offset = 0
        self.url_input = ""
        self.selected_link = 0
        
        # History and bookmarks
        self.history = []
        self.bookmarks = []
        
        # Loading state
        self.loading = False
        self.error = None
        
        self._load_bookmarks()
    
    def _load_bookmarks(self):
        """Load bookmarks."""
        path = os.path.expanduser('~/.piwrist_bookmarks.json')
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.bookmarks = json.load(f)
        except Exception:
            self.bookmarks = [
                {'name': 'Wikipedia', 'url': 'https://en.wikipedia.org/wiki/Main_Page'},
                {'name': 'Hacker News', 'url': 'https://news.ycombinator.com'},
                {'name': 'Weather', 'url': 'https://wttr.in/?format=3'},
            ]
    
    def _save_bookmarks(self):
        """Save bookmarks."""
        path = os.path.expanduser('~/.piwrist_bookmarks.json')
        try:
            with open(path, 'w') as f:
                json.dump(self.bookmarks, f)
        except Exception:
            pass
    
    def add_bookmark(self, name: str, url: str):
        """Add a bookmark."""
        self.bookmarks.append({'name': name, 'url': url})
        self._save_bookmarks()
    
    def on_enter(self):
        self.mode = 'home'
    
    def on_exit(self):
        pass
    
    def navigate(self, url: str):
        """Navigate to URL."""
        # Add protocol if missing
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        self.current_url = url
        self.loading = True
        self.error = None
        self.scroll_offset = 0
        
        try:
            # Fetch page
            headers = {'User-Agent': 'PiWrist/1.0 (Text Browser)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML to text
            parser = HTMLToText()
            parser.feed(response.text)
            
            self.page_text = parser.get_text()
            self.page_links = parser.get_links()
            
            # Clean up text
            self.page_text = re.sub(r'\n\s*\n', '\n\n', self.page_text)
            self.page_text = self.page_text.strip()
            
            # Add to history
            if not self.history or self.history[-1] != url:
                self.history.append(url)
                if len(self.history) > 50:
                    self.history.pop(0)
            
            self.mode = 'browse'
            
        except requests.exceptions.RequestException as e:
            self.error = f"Network error: {str(e)[:30]}"
        except Exception as e:
            self.error = str(e)[:40]
        finally:
            self.loading = False
    
    def go_back(self):
        """Go back in history."""
        if len(self.history) > 1:
            self.history.pop()  # Remove current
            prev_url = self.history[-1]
            self.history.pop()  # Will be re-added by navigate
            self.navigate(prev_url)
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'home':
            return self._handle_home_key(event)
        elif self.mode == 'browse':
            return self._handle_browse_key(event)
        elif self.mode == 'url_input':
            return self._handle_url_input_key(event)
        elif self.mode == 'link_select':
            return self._handle_link_select_key(event)
        return False
    
    def _handle_home_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ENTER or event.char == 'g':
            self.mode = 'url_input'
            self.url_input = ""
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_link = min(len(self.bookmarks) - 1, self.selected_link + 1)
            return True
        elif event.code == KeyCode.UP:
            self.selected_link = max(0, self.selected_link - 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.bookmarks:
                self.navigate(self.bookmarks[self.selected_link]['url'])
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        # Number shortcuts for bookmarks
        if event.char and event.char.isdigit():
            idx = int(event.char) - 1
            if 0 <= idx < len(self.bookmarks):
                self.navigate(self.bookmarks[idx]['url'])
            return True
        
        return False
    
    def _handle_browse_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
            return True
        elif event.code == KeyCode.DOWN:
            self.scroll_offset += 1
            return True
        elif event.code == KeyCode.LEFT:
            self.go_back()
            return True
        elif event.char == 'g' or event.char == 'G':
            self.mode = 'url_input'
            self.url_input = ""
            return True
        elif event.char == 'l' or event.char == 'L':
            if self.page_links:
                self.mode = 'link_select'
                self.selected_link = 0
            return True
        elif event.char == 'b' or event.char == 'B':
            # Add bookmark
            self.add_bookmark(self.current_url[:20], self.current_url)
            return True
        elif event.char == 'h' or event.char == 'H':
            self.mode = 'home'
            return True
        elif event.code == KeyCode.ESC:
            self.mode = 'home'
            return True
        return False
    
    def _handle_url_input_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ENTER:
            if self.url_input:
                self.navigate(self.url_input)
            return True
        elif event.code == KeyCode.ESC:
            self.mode = 'home' if not self.page_text else 'browse'
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.url_input:
                self.url_input = self.url_input[:-1]
            return True
        elif event.char:
            self.url_input += event.char
            return True
        return False
    
    def _handle_link_select_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            self.selected_link = max(0, self.selected_link - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_link = min(len(self.page_links) - 1, self.selected_link + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.page_links:
                link = self.page_links[self.selected_link]
                # Handle relative URLs
                if link.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(self.current_url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith('http'):
                    link = self.current_url.rsplit('/', 1)[0] + '/' + link
                self.navigate(link)
            return True
        elif event.code == KeyCode.ESC:
            self.mode = 'browse'
            return True
        
        # Number input to jump to link
        if event.char and event.char.isdigit():
            num = ""
            num += event.char
            # Could accumulate digits for multi-digit link numbers
            try:
                idx = int(num)
                if 0 <= idx < len(self.page_links):
                    self.selected_link = idx
            except:
                pass
            return True
        
        return False
    
    def draw(self, display: Display):
        """Draw browser."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        if self.loading:
            display.text(display.width // 2, display.height // 2,
                        'Loading...', 'white', 14, 'mm')
            return
        
        if self.error:
            display.text(display.width // 2, display.height // 2 - 10,
                        'Error', '#ff4444', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        self.error, '#888888', 10, 'mm')
            display.text(display.width // 2, display.height // 2 + 30,
                        'Press ESC', '#666666', 10, 'mm')
            return
        
        if self.mode == 'home':
            self._draw_home(display)
        elif self.mode == 'browse':
            self._draw_browse(display)
        elif self.mode == 'url_input':
            self._draw_url_input(display)
        elif self.mode == 'link_select':
            self._draw_link_select(display)
    
    def _draw_home(self, display: Display):
        """Draw home screen with bookmarks."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 15,
                    'Web Browser', 'white', 16, 'mm')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 35,
                    'G: Enter URL', '#666666', 11, 'mm')
        
        # Bookmarks
        y = self.ui.STATUS_BAR_HEIGHT + 60
        display.text(10, y, 'Bookmarks:', '#888888', 12)
        y += 20
        
        for i, bm in enumerate(self.bookmarks[:8]):
            selected = (i == self.selected_link)
            if selected:
                display.rect(5, y, display.width - 10, 25, fill='#0066cc')
            
            display.text(15, y + 5, f"{i+1}. {bm['name'][:25]}", 
                        'white' if selected else '#aaaaaa', 11)
            y += 28
    
    def _draw_browse(self, display: Display):
        """Draw page content."""
        # URL bar
        url_display = self.current_url[:35] + '...' if len(self.current_url) > 35 else self.current_url
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 20, fill='#1a1a2e')
        display.text(5, self.ui.STATUS_BAR_HEIGHT + 3, url_display, '#888888', 10)
        
        # Help bar
        display.text(display.width - 5, self.ui.STATUS_BAR_HEIGHT + 3,
                    'G:URL L:Links', '#444444', 8, 'rt')
        
        # Content
        content_y = self.ui.STATUS_BAR_HEIGHT + 25
        lines = self.page_text.split('\n')
        line_height = 14
        max_lines = (display.height - content_y - 5) // line_height
        
        visible = lines[self.scroll_offset:self.scroll_offset + max_lines]
        for i, line in enumerate(visible):
            y = content_y + i * line_height
            # Wrap long lines
            display.text(5, y, line[:40], 'white', 11)
        
        # Scroll indicator
        if len(lines) > max_lines:
            scroll_pct = self.scroll_offset / max(1, len(lines) - max_lines)
            indicator_h = max(20, (display.height - content_y) * max_lines // len(lines))
            indicator_y = content_y + int((display.height - content_y - indicator_h) * scroll_pct)
            display.rect(display.width - 3, indicator_y, 2, indicator_h, fill='#333333')
    
    def _draw_url_input(self, display: Display):
        """Draw URL input."""
        display.rect(10, display.height // 2 - 30, display.width - 20, 60,
                    fill='#1a1a2e', color='#0066cc')
        
        display.text(display.width // 2, display.height // 2 - 15,
                    'Enter URL:', 'white', 12, 'mm')
        
        # Input field
        display.rect(20, display.height // 2, display.width - 40, 25,
                    fill='#0a0a1a', color='#333333')
        
        url_text = self.url_input[-30:] if len(self.url_input) > 30 else self.url_input
        display.text(25, display.height // 2 + 5, url_text + '_', 'white', 11)
    
    def _draw_link_select(self, display: Display):
        """Draw link selection."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Select Link', 'white', 14, 'mm')
        
        y = self.ui.STATUS_BAR_HEIGHT + 30
        max_visible = (display.height - y - 10) // 25
        
        start = max(0, self.selected_link - max_visible // 2)
        visible = self.page_links[start:start + max_visible]
        
        for i, link in enumerate(visible):
            idx = start + i
            selected = (idx == self.selected_link)
            
            if selected:
                display.rect(5, y, display.width - 10, 22, fill='#0066cc')
            
            link_display = f"[{idx}] {link[:35]}"
            display.text(10, y + 4, link_display, 
                        'white' if selected else '#aaaaaa', 10)
            y += 25

