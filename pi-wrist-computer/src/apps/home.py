"""
Home Screen Application

Displays app grid with icons for launching applications.
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
    
    def __init__(self, rect: Rect, app_info: AppInfo, on_launch: callable):
        super().__init__(rect)
        self.app_info = app_info
        self.on_launch = on_launch
        self.hovered = False
    
    def draw(self, display: Display):
        if not self.visible:
            return
        
        cx, cy = self.rect.center
        cy -= 8  # Shift up for label
        
        # Background circle (highlight if selected/hovered)
        if self.focused or self.hovered:
            display.circle(cx, cy, self.ICON_SIZE // 2 + 4, 
                          fill='#0066cc', color='#0088ff')
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
    
    def on_enter(self):
        """Setup home screen."""
        self._build_grid()
    
    def on_exit(self):
        """Cleanup."""
        pass
    
    def _build_grid(self):
        """Build app icon grid."""
        self._app_icons = []
        
        # Get all registered apps except home
        apps = [app for app_id, app in self.ui.apps.items() 
                if app_id != 'home']
        
        # Calculate grid layout
        start_x = (self.ui.display.width - self.GRID_COLS * self.ICON_WIDTH) // 2
        start_y = self.ui.STATUS_BAR_HEIGHT + 10
        
        for i, app in enumerate(apps):
            if i >= self.GRID_COLS * self.GRID_ROWS:
                break  # Only show one page for now
            
            row = i // self.GRID_COLS
            col = i % self.GRID_COLS
            
            x = start_x + col * self.ICON_WIDTH
            y = start_y + row * self.ICON_HEIGHT
            
            icon = AppIcon(
                Rect(x, y, self.ICON_WIDTH, self.ICON_HEIGHT),
                app.info,
                self._launch_app
            )
            self._app_icons.append(icon)
        
        # Set initial selection
        if self._app_icons:
            self._app_icons[0].focused = True
    
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
                self._app_icons[idx].on_launch(
                    self._app_icons[idx].app_info.id
                )
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
        
        # Draw all app icons
        for icon in self._app_icons:
            icon.draw(display)
        
        # Page indicator (if multiple pages)
        # TODO: Implement pagination

