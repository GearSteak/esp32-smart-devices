"""
Flappy Bird Clone
Tap to fly through pipes.
"""

import time
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class FlappyApp(App):
    """Flappy Bird clone."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='flappy',
            name='Flappy Bird',
            icon='🐦',
            color='#ffdd00'
        )
        
        self.bird_x = 60
        self.bird_y = 0
        self.bird_velocity = 0
        self.gravity = 0.5
        self.flap_strength = -8
        
        self.pipes = []
        self.pipe_width = 40
        self.pipe_gap = 90
        self.pipe_speed = 3
        
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.started = False
        self.last_update = 0
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        self.bird_y = self.ui.display.height // 2
        self.bird_velocity = 0
        self.pipes = []
        self.score = 0
        self.game_over = False
        self.started = False
        self._spawn_pipe()
    
    def _spawn_pipe(self):
        """Spawn a new pipe."""
        gap_y = random.randint(self.ui.STATUS_BAR_HEIGHT + 60, 
                               self.ui.display.height - 60 - self.pipe_gap)
        self.pipes.append({
            'x': self.ui.display.width,
            'gap_y': gap_y,
            'scored': False
        })
    
    def _flap(self):
        """Make the bird flap."""
        self.bird_velocity = self.flap_strength
        if not self.started:
            self.started = True
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if event.code == KeyCode.ENTER or event.char == ' ' or event.code == KeyCode.UP:
            self._flap()
        
        return True
    
    def _update(self):
        """Update game state."""
        if self.game_over or not self.started:
            return
        
        now = time.time()
        if now - self.last_update < 0.025:
            return
        self.last_update = now
        
        # Bird physics
        self.bird_velocity += self.gravity
        self.bird_y += self.bird_velocity
        
        # Bounds check
        if self.bird_y < self.ui.STATUS_BAR_HEIGHT:
            self.bird_y = self.ui.STATUS_BAR_HEIGHT
            self.bird_velocity = 0
        elif self.bird_y > self.ui.display.height - 20:
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
        
        # Move pipes
        for pipe in self.pipes:
            pipe['x'] -= self.pipe_speed
            
            # Score
            if not pipe['scored'] and pipe['x'] + self.pipe_width < self.bird_x:
                pipe['scored'] = True
                self.score += 1
            
            # Collision
            if (pipe['x'] < self.bird_x + 20 < pipe['x'] + self.pipe_width):
                if self.bird_y < pipe['gap_y'] or self.bird_y + 15 > pipe['gap_y'] + self.pipe_gap:
                    self.game_over = True
                    if self.score > self.high_score:
                        self.high_score = self.score
        
        # Remove off-screen pipes and spawn new ones
        self.pipes = [p for p in self.pipes if p['x'] > -self.pipe_width]
        
        if not self.pipes or self.pipes[-1]['x'] < self.ui.display.width - 150:
            self._spawn_pipe()
    
    def draw(self, display: Display):
        self._update()
        
        # Sky background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#70c5ce')
        
        # Ground
        display.rect(0, display.height - 20, display.width, 20, fill='#ded895')
        
        # Pipes
        for pipe in self.pipes:
            # Top pipe
            display.rect(int(pipe['x']), self.ui.STATUS_BAR_HEIGHT,
                        self.pipe_width, pipe['gap_y'] - self.ui.STATUS_BAR_HEIGHT, fill='#73bf2e')
            display.rect(int(pipe['x']) - 3, pipe['gap_y'] - 20, 
                        self.pipe_width + 6, 20, fill='#73bf2e')
            
            # Bottom pipe
            bottom_y = pipe['gap_y'] + self.pipe_gap
            display.rect(int(pipe['x']), bottom_y,
                        self.pipe_width, display.height - 20 - bottom_y, fill='#73bf2e')
            display.rect(int(pipe['x']) - 3, bottom_y, 
                        self.pipe_width + 6, 20, fill='#73bf2e')
        
        # Bird
        bird_color = '#f7dc6f' if not self.game_over else '#ff6666'
        display.circle(self.bird_x + 10, int(self.bird_y) + 10, 12, fill=bird_color)
        display.circle(self.bird_x + 18, int(self.bird_y) + 8, 4, fill='white')
        display.circle(self.bird_x + 19, int(self.bird_y) + 8, 2, fill='black')
        
        # Beak
        display.rect(self.bird_x + 20, int(self.bird_y) + 10, 8, 4, fill='#e74c3c')
        
        # Score
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 25,
                    str(self.score), 'white', 28, 'mm')
        
        # Start message
        if not self.started and not self.game_over:
            display.text(display.width // 2, display.height // 2,
                        "TAP TO START", '#ffffff', 14, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 - 40, display.width - 60, 80,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 20,
                        "GAME OVER", '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 5,
                        f"Score: {self.score}", 'white', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 25,
                        f"Best: {self.high_score}", '#888888', 12, 'mm')

