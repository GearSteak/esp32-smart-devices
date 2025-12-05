"""
Home Screen Application

Displays app grid with icons for launching applications.
Supports app grouping (folders).
"""

from ..ui.framework import App, AppInfo, Rect, Widget
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from PIL import Image, ImageDraw
import math


class AppIcon(Widget):
    """App icon widget for home screen."""
    
    ICON_SIZE = 48
    LABEL_HEIGHT = 16
    
    def __init__(self, rect: Rect, app_info: AppInfo, on_launch: callable, is_folder: bool = False):
        super().__init__(rect)
        self.app_info = app_info
        self.on_launch = on_launch
        self.hovered = False
        self.is_folder = is_folder
    
    def draw(self, display: Display):
        if not self.visible:
            return
        
        cx, cy = self.rect.center
        cy -= 8  # Shift up for label
        
        # Background circle (highlight if selected/hovered)
        if self.focused or self.hovered:
            display.circle(cx, cy, self.ICON_SIZE // 2 + 4, 
                          fill='#0066cc', color='#0088ff')
        elif self.is_folder:
            display.circle(cx, cy, self.ICON_SIZE // 2, 
                          fill='#2a2a4a', color='#4a4a6a')
        else:
            display.circle(cx, cy, self.ICON_SIZE // 2, 
                          fill='#333333', color='#444444')
        
        # Icon character
        display.text(cx, cy, self.app_info.icon, 
                    self.app_info.color, 24, 'mm')
        
        # Label below
        display.text(cx, self.rect.y + self.rect.height - 4,
                    self.app_info.name, 'white', 10, 'mb')
    
    def on_click(self, x: int, y: int) -> bool:
        if self.rect.contains(x, y) and self.on_launch:
            self.on_launch(self.app_info.id)
            return True
        return False
    
    def on_cursor_move(self, x: int, y: int):
        self.hovered = self.rect.contains(x, y)


class HomeApp(App):
    """Home screen with app launcher grid."""
    
    GRID_COLS = 4
    GRID_ROWS = 4
    ICON_WIDTH = 60
    ICON_HEIGHT = 70
    
    # App categories/folders
    APP_GROUPS = {
        'games': {
            'name': 'Games',
            'icon': '🎮',
            'color': '#ff6b6b',
            'apps': [
                'tetris', 'snake', '2048', 'solitaire',
                'minesweeper', 'pong', 'breakout', 'wordle',
                'flappy', 'connect4', 'simon', 'hangman',
                'puzzle15', 'memory', 'rps', 'tictactoe',
                'blackjack', 'invaders', 'asteroids',
                'checkers', 'chess', 'uno',
                'pinball', 'gamewatch',
            ]
        },
        'ttrpg': {
            'name': 'TTRPG',
            'icon': '⚔',
            'color': '#c0392b',
            'apps': ['ttrpg', 'dice', 'light_tracker']
        },
        'tools': {
            'name': 'Tools',
            'icon': '🔧',
            'color': '#888888',
            'apps': ['calculator', 'notes', 'calendar', 'passwords']
        },
        'media': {
            'name': 'Media',
            'icon': '🎬', 
            'color': '#ff69b4',
            'apps': ['media', 'spotify']
        }
    }
    
    # Apps to show directly on home (not in folders)
    MAIN_APPS = ['settings', 'weather', 'email', 'browser', 'navigation', 'notifications']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='home',
            name='Home',
            icon='⌂',
            color='#ffffff'
        )
        
        self.selected_row = 0
        self.selected_col = 0
        self.page = 0
        self._app_icons = []
        
        # Folder state
        self.in_folder = False
        self.current_folder = None
        self.folder_items = []
        self.folder_selected = 0
        self.folder_scroll = 0  # Scroll offset for folder view
    
    def on_enter(self):
        """Setup home screen."""
        self.selected_row = 0
        self.selected_col = 0
        self.in_folder = False
        self.current_folder = None
        self._build_grid()
    
    def on_exit(self):
        """Cleanup."""
        pass
    
    def _build_grid(self):
        """Build app icon grid."""
        self._app_icons = []
        
        # Calculate grid layout
        start_x = (self.ui.display.width - self.GRID_COLS * self.ICON_WIDTH) // 2
        start_y = self.ui.STATUS_BAR_HEIGHT + 10
        
        items = []
        
        # Add folders first
        for folder_id, folder_info in self.APP_GROUPS.items():
            items.append({
                'id': f'folder_{folder_id}',
                'info': AppInfo(
                    id=f'folder_{folder_id}',
                    name=folder_info['name'],
                    icon=folder_info['icon'],
                    color=folder_info['color']
                ),
                'is_folder': True,
                'folder_id': folder_id
            })
        
        # Add main apps
        for app_id in self.MAIN_APPS:
            if app_id in self.ui.apps:
                app = self.ui.apps[app_id]
                items.append({
                    'id': app_id,
                    'info': app.info,
                    'is_folder': False
                })
        
        # Create icons
        for i, item in enumerate(items):
            if i >= self.GRID_COLS * self.GRID_ROWS:
                break
            
            row = i // self.GRID_COLS
            col = i % self.GRID_COLS
            
            x = start_x + col * self.ICON_WIDTH
            y = start_y + row * self.ICON_HEIGHT
            
            icon = AppIcon(
                Rect(x, y, self.ICON_WIDTH, self.ICON_HEIGHT),
                item['info'],
                lambda item_id=item['id'], is_folder=item['is_folder'], 
                       folder_id=item.get('folder_id'): self._handle_select(item_id, is_folder, folder_id),
                is_folder=item['is_folder']
            )
            self._app_icons.append(icon)
        
        # Set initial selection
        if self._app_icons:
            self._app_icons[0].focused = True
    
    def _handle_select(self, item_id: str, is_folder: bool, folder_id: str = None):
        """Handle item selection."""
        if is_folder and folder_id:
            self._open_folder(folder_id)
        else:
            self._launch_app(item_id)
    
    def _open_folder(self, folder_id: str):
        """Open a folder."""
        if folder_id not in self.APP_GROUPS:
            return
        
        folder = self.APP_GROUPS[folder_id]
        self.current_folder = folder_id
        self.folder_items = []
        self.folder_selected = 0
        self.folder_scroll = 0  # Reset scroll when opening folder
        
        for app_id in folder['apps']:
            if app_id in self.ui.apps:
                self.folder_items.append(self.ui.apps[app_id])
        
        self.in_folder = True
    
    def _close_folder(self):
        """Close current folder."""
        self.in_folder = False
        self.current_folder = None
        self.folder_items = []
    
    def _launch_app(self, app_id: str):
        """Launch an app by ID."""
        self.ui.launch_app(app_id)
    
    def _get_selected_index(self) -> int:
        """Get currently selected icon index."""
        return self.selected_row * self.GRID_COLS + self.selected_col
    
    def _update_selection(self):
        """Update which icon is focused."""
        for i, icon in enumerate(self._app_icons):
            icon.focused = (i == self._get_selected_index())
    
    def on_key(self, event: KeyEvent) -> bool:
        """Handle keyboard navigation."""
        # Handle folder view
        if self.in_folder:
            return self._handle_folder_key(event)
        
        max_row = (len(self._app_icons) - 1) // self.GRID_COLS
        
        if event.code == KeyCode.UP:
            if self.selected_row > 0:
                self.selected_row -= 1
                self._update_selection()
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_row < max_row:
                self.selected_row += 1
                # Clamp column if needed
                idx = self._get_selected_index()
                if idx >= len(self._app_icons):
                    self.selected_col = (len(self._app_icons) - 1) % self.GRID_COLS
                self._update_selection()
            return True
        elif event.code == KeyCode.LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
                self._update_selection()
            return True
        elif event.code == KeyCode.RIGHT:
            if self.selected_col < self.GRID_COLS - 1:
                idx = self._get_selected_index() + 1
                if idx < len(self._app_icons):
                    self.selected_col += 1
                    self._update_selection()
            return True
        elif event.code == KeyCode.ENTER:
            idx = self._get_selected_index()
            if 0 <= idx < len(self._app_icons):
                # Trigger the icon's callback
                icon = self._app_icons[idx]
                icon.on_launch(icon.app_info.id)
            return True
        
        return False
    
    def _handle_folder_key(self, event: KeyEvent) -> bool:
        """Handle keys in folder view."""
        # Calculate visible items
        item_height = 50
        header_height = 45
        available_height = self.ui.display.height - self.ui.STATUS_BAR_HEIGHT - header_height - 10
        max_visible = available_height // item_height
        
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self._close_folder()
            return True
        elif event.code == KeyCode.UP:
            if self.folder_selected > 0:
                self.folder_selected -= 1
                # Scroll up if needed
                if self.folder_selected < self.folder_scroll:
                    self.folder_scroll = self.folder_selected
            return True
        elif event.code == KeyCode.DOWN:
            if self.folder_selected < len(self.folder_items) - 1:
                self.folder_selected += 1
                # Scroll down if needed
                if self.folder_selected >= self.folder_scroll + max_visible:
                    self.folder_scroll = self.folder_selected - max_visible + 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.folder_items:
                app = self.folder_items[self.folder_selected]
                self._close_folder()
                self._launch_app(app.info.id)
            return True
        return False
    
    def on_click(self, x: int, y: int) -> bool:
        """Handle click on icons."""
        for icon in self._app_icons:
            if icon.on_click(x, y):
                return True
        return False
    
    def on_cursor_move(self, x: int, y: int):
        """Update hover states."""
        for icon in self._app_icons:
            icon.on_cursor_move(x, y)
    
    def draw(self, display: Display):
        """Draw home screen."""
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, 
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        if self.in_folder:
            self._draw_folder(display)
        else:
            # Draw all app icons
            for icon in self._app_icons:
                icon.draw(display)
    
    def _draw_folder(self, display: Display):
        """Draw folder contents with scrolling."""
        if not self.current_folder:
            return
        
        folder = self.APP_GROUPS[self.current_folder]
        
        # Folder header
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 35, fill='#1a1a2e')
        display.text(15, self.ui.STATUS_BAR_HEIGHT + 17, folder['icon'], folder['color'], 18, 'lm')
        display.text(45, self.ui.STATUS_BAR_HEIGHT + 17, folder['name'], 'white', 16, 'lm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 17, '< Back', '#666666', 10, 'rm')
        
        # App list with scrolling
        item_height = 50
        header_height = 45
        start_y = self.ui.STATUS_BAR_HEIGHT + header_height
        available_height = display.height - self.ui.STATUS_BAR_HEIGHT - header_height - 10
        max_visible = available_height // item_height
        
        # Draw visible items only
        for i in range(max_visible):
            item_index = self.folder_scroll + i
            if item_index >= len(self.folder_items):
                break
            
            app = self.folder_items[item_index]
            y = start_y + i * item_height
            selected = (item_index == self.folder_selected)
            
            if selected:
                display.rect(10, y, display.width - 20, item_height - 5, fill='#0066cc')
            else:
                display.rect(10, y, display.width - 20, item_height - 5, fill='#1a1a2e')
            
            # Icon
            display.text(30, y + item_height // 2 - 2, app.info.icon, app.info.color, 20, 'mm')
            
            # Name
            display.text(60, y + item_height // 2 - 2, app.info.name, 'white', 14, 'lm')
        
        # Scroll indicators
        if self.folder_scroll > 0:
            display.text(display.width // 2, start_y - 8, '▲', '#888888', 12, 'mm')
        
        if self.folder_scroll + max_visible < len(self.folder_items):
            display.text(display.width // 2, display.height - 8, '▼', '#888888', 12, 'mm')
        
        # Item count
        display.text(display.width - 10, display.height - 8, 
                    f'{self.folder_selected + 1}/{len(self.folder_items)}', '#666666', 10, 'rm')

