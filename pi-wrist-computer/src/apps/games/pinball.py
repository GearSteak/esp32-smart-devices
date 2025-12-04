"""
Pinball Game
Simple pinball with flippers.
"""

import time
import math
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class PinballApp(App):
    """Simple pinball game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='pinball',
            name='Pinball',
            icon='🎱',
            color='#c0392b'
        )
        
        self.ball_x = 0
        self.ball_y = 0
        self.ball_vx = 0
        self.ball_vy = 0
        self.ball_radius = 6
        
        self.left_flipper = 0  # Angle offset
        self.right_flipper = 0
        
        self.bumpers = []
        self.targets = []
        
        self.score = 0
        self.balls_left = 3
        self.game_over = False
        self.ball_in_play = False
        self.last_update = 0
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start new game."""
        self.score = 0
        self.balls_left = 3
        self.game_over = False
        self._setup_table()
        self._launch_ball()
    
    def _setup_table(self):
        """Setup pinball table elements."""
        w = self.ui.display.width
        h = self.ui.display.height
        
        # Bumpers (x, y, radius, points)
        self.bumpers = [
            (w // 3, h // 3, 15, 100),
            (2 * w // 3, h // 3, 15, 100),
            (w // 2, h // 4, 20, 500),
        ]
        
        # Targets (x, y, width, height, points, active)
        self.targets = [
            [30, h // 2 - 40, 15, 30, 250, True],
            [w - 45, h // 2 - 40, 15, 30, 250, True],
            [w // 2 - 30, self.ui.STATUS_BAR_HEIGHT + 40, 60, 10, 1000, True],
        ]
    
    def _launch_ball(self):
        """Launch a new ball."""
        w = self.ui.display.width
        
        self.ball_x = w - 20
        self.ball_y = self.ui.display.height - 100
        self.ball_vx = random.uniform(-2, -1)
        self.ball_vy = random.uniform(-8, -6)
        self.ball_in_play = True
        
        # Reset targets
        for target in self.targets:
            target[5] = True
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if not self.ball_in_play:
            if event.code == KeyCode.ENTER:
                self._launch_ball()
            return True
        
        # Flippers
        if event.code == KeyCode.LEFT or event.char == 'z' or event.char == 'Z':
            self.left_flipper = 30
        elif event.code == KeyCode.RIGHT or event.char == 'm' or event.char == 'M':
            self.right_flipper = 30
        
        return True
    
    def _update(self):
        """Update physics."""
        if self.game_over or not self.ball_in_play:
            return
        
        now = time.time()
        if now - self.last_update < 0.016:  # ~60 FPS
            return
        self.last_update = now
        
        w = self.ui.display.width
        h = self.ui.display.height
        
        # Gravity
        self.ball_vy += 0.3
        
        # Apply velocity
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        
        # Wall bounces
        if self.ball_x < self.ball_radius:
            self.ball_x = self.ball_radius
            self.ball_vx = -self.ball_vx * 0.8
        elif self.ball_x > w - self.ball_radius:
            self.ball_x = w - self.ball_radius
            self.ball_vx = -self.ball_vx * 0.8
        
        if self.ball_y < self.ui.STATUS_BAR_HEIGHT + self.ball_radius:
            self.ball_y = self.ui.STATUS_BAR_HEIGHT + self.ball_radius
            self.ball_vy = -self.ball_vy * 0.8
        
        # Bumper collisions
        for bx, by, br, points in self.bumpers:
            dx = self.ball_x - bx
            dy = self.ball_y - by
            dist = math.sqrt(dx * dx + dy * dy)
            
            if dist < br + self.ball_radius:
                # Bounce off bumper
                angle = math.atan2(dy, dx)
                speed = math.sqrt(self.ball_vx ** 2 + self.ball_vy ** 2)
                self.ball_vx = math.cos(angle) * speed * 1.2
                self.ball_vy = math.sin(angle) * speed * 1.2
                self.ball_x = bx + math.cos(angle) * (br + self.ball_radius + 1)
                self.ball_y = by + math.sin(angle) * (br + self.ball_radius + 1)
                self.score += points
        
        # Target collisions
        for target in self.targets:
            if not target[5]:
                continue
            tx, ty, tw, th = target[:4]
            if (tx < self.ball_x < tx + tw and ty < self.ball_y < ty + th):
                target[5] = False
                self.score += target[4]
                self.ball_vy = -self.ball_vy * 0.9
        
        # Flipper collision zones
        flipper_y = h - 50
        flipper_len = 45
        
        # Left flipper
        if (30 < self.ball_x < 30 + flipper_len and 
            flipper_y - 10 < self.ball_y < flipper_y + 10):
            if self.left_flipper > 0:
                self.ball_vy = -abs(self.ball_vy) - 8
                self.ball_vx = (self.ball_x - 30) / 10
        
        # Right flipper
        if (w - 30 - flipper_len < self.ball_x < w - 30 and
            flipper_y - 10 < self.ball_y < flipper_y + 10):
            if self.right_flipper > 0:
                self.ball_vy = -abs(self.ball_vy) - 8
                self.ball_vx = -(w - 30 - self.ball_x) / 10
        
        # Decay flippers
        self.left_flipper = max(0, self.left_flipper - 5)
        self.right_flipper = max(0, self.right_flipper - 5)
        
        # Ball lost
        if self.ball_y > h:
            self.ball_in_play = False
            self.balls_left -= 1
            if self.balls_left <= 0:
                self.game_over = True
    
    def draw(self, display: Display):
        self._update()
        
        w = display.width
        h = display.height
        
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, w, h - self.ui.STATUS_BAR_HEIGHT, 
                    fill='#1a0a2e')
        
        # Score
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 15, f"{self.score:,}", '#ffff00', 14)
        display.text(w - 10, self.ui.STATUS_BAR_HEIGHT + 15, 
                    "●" * self.balls_left, '#ff0000', 12, 'rt')
        
        # Bumpers
        for bx, by, br, _ in self.bumpers:
            display.circle(bx, by, br, fill='#ff6600', outline='#ffaa00')
        
        # Targets
        for target in self.targets:
            tx, ty, tw, th, _, active = target
            color = '#00ff00' if active else '#333333'
            display.rect(tx, ty, tw, th, fill=color)
        
        # Flippers
        flipper_y = h - 50
        flipper_len = 45
        
        # Left flipper
        left_angle = -self.left_flipper
        display.rect(30, flipper_y - 5, flipper_len, 10, fill='#ffffff')
        
        # Right flipper  
        right_angle = self.right_flipper
        display.rect(w - 30 - flipper_len, flipper_y - 5, flipper_len, 10, fill='#ffffff')
        
        # Ball
        if self.ball_in_play:
            display.circle(int(self.ball_x), int(self.ball_y), self.ball_radius, fill='#c0c0c0')
        
        # Drain gutter
        display.rect(0, h - 10, w, 10, fill='#000000')
        
        # Launch prompt
        if not self.ball_in_play and not self.game_over:
            display.text(w // 2, h // 2, "PRESS ENTER", '#ffffff', 14, 'mm')
            display.text(w // 2, h // 2 + 20, "to launch ball", '#888888', 10, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, h // 2 - 30, w - 60, 60, fill='#000000', outline='white')
            display.text(w // 2, h // 2 - 10, "GAME OVER", '#ff0000', 16, 'mm')
            display.text(w // 2, h // 2 + 10, f"Score: {self.score:,}", 'white', 12, 'mm')
        
        # Controls hint
        if self.ball_in_play:
            display.text(w // 2, h - 15, "← Left  Right →", '#555555', 9, 'mm')

