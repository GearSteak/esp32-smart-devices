"""
Pong Game
Classic paddle ball game.
"""

import time
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class PongApp(App):
    """Classic Pong game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='pong',
            name='Pong',
            icon='🏓',
            color='#00ff00'
        )
        
        self.paddle_height = 40
        self.paddle_width = 8
        self.ball_size = 8
        self.paddle_speed = 8
        self.ball_speed = 4
        
        self.player_y = 0
        self.ai_y = 0
        self.ball_x = 0
        self.ball_y = 0
        self.ball_dx = 0
        self.ball_dy = 0
        
        self.player_score = 0
        self.ai_score = 0
        self.paused = False
        self.last_update = 0
    
    def on_enter(self):
        self._reset_game()
    
    def _reset_game(self):
        """Reset the game state."""
        self.player_y = (self.ui.display.height - self.paddle_height) // 2
        self.ai_y = self.player_y
        self._reset_ball()
        self.player_score = 0
        self.ai_score = 0
        self.paused = False
    
    def _reset_ball(self):
        """Reset ball to center."""
        self.ball_x = self.ui.display.width // 2
        self.ball_y = self.ui.display.height // 2
        self.ball_dx = self.ball_speed * random.choice([-1, 1])
        self.ball_dy = self.ball_speed * random.uniform(-0.5, 0.5)
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if event.code == KeyCode.UP:
            self.player_y = max(self.ui.STATUS_BAR_HEIGHT, 
                               self.player_y - self.paddle_speed)
        elif event.code == KeyCode.DOWN:
            self.player_y = min(self.ui.display.height - self.paddle_height,
                               self.player_y + self.paddle_speed)
        elif event.char == ' ' or event.code == KeyCode.ENTER:
            self.paused = not self.paused
        elif event.char == 'n' or event.char == 'N':
            self._reset_game()
        
        return True
    
    def _update(self):
        """Update game state."""
        if self.paused:
            return
        
        now = time.time()
        if now - self.last_update < 0.03:  # ~30 FPS
            return
        self.last_update = now
        
        # Move ball
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # Ball collision with top/bottom
        if self.ball_y <= self.ui.STATUS_BAR_HEIGHT:
            self.ball_y = self.ui.STATUS_BAR_HEIGHT
            self.ball_dy = -self.ball_dy
        elif self.ball_y >= self.ui.display.height - self.ball_size:
            self.ball_y = self.ui.display.height - self.ball_size
            self.ball_dy = -self.ball_dy
        
        # Ball collision with player paddle
        if (self.ball_x <= self.paddle_width + 10 and
            self.player_y <= self.ball_y <= self.player_y + self.paddle_height):
            self.ball_dx = abs(self.ball_dx) * 1.05  # Speed up slightly
            # Add spin based on where ball hits paddle
            hit_pos = (self.ball_y - self.player_y) / self.paddle_height
            self.ball_dy = (hit_pos - 0.5) * self.ball_speed * 2
        
        # Ball collision with AI paddle
        if (self.ball_x >= self.ui.display.width - self.paddle_width - 10 - self.ball_size and
            self.ai_y <= self.ball_y <= self.ai_y + self.paddle_height):
            self.ball_dx = -abs(self.ball_dx) * 1.05
            hit_pos = (self.ball_y - self.ai_y) / self.paddle_height
            self.ball_dy = (hit_pos - 0.5) * self.ball_speed * 2
        
        # Score
        if self.ball_x <= 0:
            self.ai_score += 1
            self._reset_ball()
        elif self.ball_x >= self.ui.display.width:
            self.player_score += 1
            self._reset_ball()
        
        # AI movement
        ai_center = self.ai_y + self.paddle_height // 2
        if self.ball_y < ai_center - 10:
            self.ai_y = max(self.ui.STATUS_BAR_HEIGHT, self.ai_y - self.paddle_speed * 0.7)
        elif self.ball_y > ai_center + 10:
            self.ai_y = min(self.ui.display.height - self.paddle_height, 
                           self.ai_y + self.paddle_speed * 0.7)
    
    def draw(self, display: Display):
        self._update()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#000000')
        
        # Center line
        for y in range(self.ui.STATUS_BAR_HEIGHT, display.height, 20):
            display.rect(display.width // 2 - 1, y, 2, 10, fill='#333333')
        
        # Score
        display.text(display.width // 4, self.ui.STATUS_BAR_HEIGHT + 20,
                    str(self.player_score), 'white', 24, 'mm')
        display.text(3 * display.width // 4, self.ui.STATUS_BAR_HEIGHT + 20,
                    str(self.ai_score), 'white', 24, 'mm')
        
        # Player paddle
        display.rect(10, int(self.player_y), self.paddle_width, self.paddle_height, fill='#00ff00')
        
        # AI paddle
        display.rect(display.width - 10 - self.paddle_width, int(self.ai_y),
                    self.paddle_width, self.paddle_height, fill='#ff0000')
        
        # Ball
        display.rect(int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size, fill='white')
        
        # Paused
        if self.paused:
            display.rect(60, display.height // 2 - 20, display.width - 120, 40,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2,
                        "PAUSED", 'white', 16, 'mm')

