"""
Game & Watch Collection
Classic LCD-style games.
"""

import time
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class GameWatchApp(App):
    """Game & Watch style games collection."""
    
    GAMES = ['Ball', 'Fire', 'Octopus']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='gamewatch',
            name='G&W',
            icon='🎮',
            color='#d4a574'
        )
        
        self.current_game = 0
        self.state = 'menu'  # menu, playing
        
        # Ball game state
        self.ball_positions = [0, 0]  # 0-3 for each hand
        self.balls = []  # List of (position, hand, timing)
        
        # Fire game state
        self.catcher_pos = 1  # 0-2
        self.fallers = []  # List of (x, y, speed)
        
        # Octopus game state
        self.diver_pos = 0  # 0-4
        self.diver_has_treasure = False
        self.tentacles = []  # List of positions
        
        # Common
        self.score = 0
        self.misses = 0
        self.max_misses = 3
        self.game_over = False
        self.last_update = 0
        self.speed = 1.0
    
    def on_enter(self):
        self.state = 'menu'
        self.current_game = 0
    
    def _start_game(self):
        """Start selected game."""
        self.score = 0
        self.misses = 0
        self.game_over = False
        self.speed = 1.0
        self.state = 'playing'
        
        if self.current_game == 0:  # Ball
            self.ball_positions = [0, 0]
            self.balls = []
            self._spawn_ball()
        elif self.current_game == 1:  # Fire
            self.catcher_pos = 1
            self.fallers = []
        elif self.current_game == 2:  # Octopus
            self.diver_pos = 0
            self.diver_has_treasure = False
            self.tentacles = [1, 3]
    
    def _spawn_ball(self):
        """Spawn a new ball for Ball game."""
        hand = random.randint(0, 1)
        self.balls.append({'pos': 3, 'hand': hand, 'timer': 0})
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            if self.state == 'playing':
                self.state = 'menu'
            else:
                self.ui.go_home()
            return True
        
        if self.state == 'menu':
            if event.code == KeyCode.UP:
                self.current_game = (self.current_game - 1) % len(self.GAMES)
            elif event.code == KeyCode.DOWN:
                self.current_game = (self.current_game + 1) % len(self.GAMES)
            elif event.code == KeyCode.ENTER:
                self._start_game()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._start_game()
            return True
        
        # Game-specific controls
        if self.current_game == 0:  # Ball
            if event.code == KeyCode.LEFT:
                self.ball_positions[0] = min(3, self.ball_positions[0] + 1)
            elif event.code == KeyCode.RIGHT:
                self.ball_positions[1] = min(3, self.ball_positions[1] + 1)
        
        elif self.current_game == 1:  # Fire
            if event.code == KeyCode.LEFT:
                self.catcher_pos = max(0, self.catcher_pos - 1)
            elif event.code == KeyCode.RIGHT:
                self.catcher_pos = min(2, self.catcher_pos + 1)
        
        elif self.current_game == 2:  # Octopus
            if event.code == KeyCode.LEFT:
                self.diver_pos = max(0, self.diver_pos - 1)
            elif event.code == KeyCode.RIGHT:
                self.diver_pos = min(4, self.diver_pos + 1)
            elif event.code == KeyCode.ENTER:
                if self.diver_pos == 4 and not self.diver_has_treasure:
                    self.diver_has_treasure = True
                elif self.diver_pos == 0 and self.diver_has_treasure:
                    self.score += 100
                    self.diver_has_treasure = False
        
        return True
    
    def _update(self):
        """Update game state."""
        if self.game_over or self.state != 'playing':
            return
        
        now = time.time()
        dt = now - self.last_update
        if dt < 0.05:
            return
        self.last_update = now
        
        if self.current_game == 0:
            self._update_ball()
        elif self.current_game == 1:
            self._update_fire()
        elif self.current_game == 2:
            self._update_octopus()
        
        # Speed up over time
        self.speed = min(2.0, 1.0 + self.score / 500)
    
    def _update_ball(self):
        """Update Ball game."""
        # Decay hand positions
        self.ball_positions[0] = max(0, self.ball_positions[0] - 0.1)
        self.ball_positions[1] = max(0, self.ball_positions[1] - 0.1)
        
        # Update balls
        for ball in self.balls[:]:
            ball['timer'] += 0.1 * self.speed
            
            if ball['timer'] >= 1:
                ball['timer'] = 0
                ball['pos'] -= 1
                
                if ball['pos'] < 0:
                    # Check catch
                    hand_pos = int(self.ball_positions[ball['hand']])
                    if hand_pos >= 2:
                        self.score += 10
                        ball['hand'] = 1 - ball['hand']
                        ball['pos'] = 3
                    else:
                        self.misses += 1
                        self.balls.remove(ball)
                        if self.misses >= self.max_misses:
                            self.game_over = True
        
        # Spawn new balls
        if random.random() < 0.02 * self.speed and len(self.balls) < 3:
            self._spawn_ball()
    
    def _update_fire(self):
        """Update Fire game."""
        # Spawn fallers
        if random.random() < 0.03 * self.speed:
            x = random.randint(0, 2)
            self.fallers.append({'x': x, 'y': 0, 'speed': 0.5 + random.random() * 0.5})
        
        # Update fallers
        for f in self.fallers[:]:
            f['y'] += f['speed'] * self.speed * 0.1
            
            if f['y'] >= 4:
                if f['x'] == self.catcher_pos:
                    self.score += 10
                else:
                    self.misses += 1
                    if self.misses >= self.max_misses:
                        self.game_over = True
                self.fallers.remove(f)
    
    def _update_octopus(self):
        """Update Octopus game."""
        # Move tentacles
        for i in range(len(self.tentacles)):
            self.tentacles[i] += random.choice([-1, 0, 1]) * 0.2
            self.tentacles[i] = max(1, min(3, self.tentacles[i]))
        
        # Check collision with diver
        if 1 <= self.diver_pos <= 3:
            for t in self.tentacles:
                if abs(t - self.diver_pos) < 0.5:
                    self.misses += 1
                    self.diver_pos = 0
                    self.diver_has_treasure = False
                    if self.misses >= self.max_misses:
                        self.game_over = True
    
    def draw(self, display: Display):
        self._update()
        
        w = display.width
        h = display.height
        
        # LCD-style background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, w, h - self.ui.STATUS_BAR_HEIGHT,
                    fill='#a8b89c')
        
        if self.state == 'menu':
            self._draw_menu(display)
        else:
            # Score display
            display.rect(10, self.ui.STATUS_BAR_HEIGHT + 5, 80, 25, fill='#8a9b7c')
            display.text(50, self.ui.STATUS_BAR_HEIGHT + 17, f"{self.score:05d}", '#2a2a2a', 14, 'mm')
            
            # Miss indicators
            for i in range(self.max_misses):
                color = '#ff0000' if i < self.misses else '#4a5b3c'
                display.circle(w - 20 - i * 20, self.ui.STATUS_BAR_HEIGHT + 17, 6, fill=color)
            
            if self.current_game == 0:
                self._draw_ball(display)
            elif self.current_game == 1:
                self._draw_fire(display)
            elif self.current_game == 2:
                self._draw_octopus(display)
            
            if self.game_over:
                display.rect(40, h // 2 - 25, w - 80, 50, fill='#2a2a2a')
                display.text(w // 2, h // 2 - 5, "GAME OVER", '#ff0000', 16, 'mm')
                display.text(w // 2, h // 2 + 15, "ENTER to retry", '#888888', 10, 'mm')
    
    def _draw_menu(self, display: Display):
        """Draw game selection menu."""
        w = display.width
        h = display.height
        
        display.text(w // 2, self.ui.STATUS_BAR_HEIGHT + 30, "GAME & WATCH", '#2a2a2a', 18, 'mm')
        
        for i, game in enumerate(self.GAMES):
            y = self.ui.STATUS_BAR_HEIGHT + 80 + i * 40
            selected = (i == self.current_game)
            
            if selected:
                display.rect(40, y - 5, w - 80, 35, fill='#6a7b5c')
            
            display.text(w // 2, y + 12, game, '#2a2a2a' if selected else '#5a6b4c', 16, 'mm')
    
    def _draw_ball(self, display: Display):
        """Draw Ball game."""
        w = display.width
        h = display.height
        center_y = self.ui.STATUS_BAR_HEIGHT + 140
        
        # Juggler hands
        left_y = center_y + 40 - int(self.ball_positions[0]) * 15
        right_y = center_y + 40 - int(self.ball_positions[1]) * 15
        
        display.rect(60, left_y, 30, 10, fill='#2a2a2a')
        display.rect(w - 90, right_y, 30, 10, fill='#2a2a2a')
        
        # Juggler body
        display.rect(w // 2 - 15, center_y + 20, 30, 50, fill='#2a2a2a')
        display.circle(w // 2, center_y, 15, fill='#2a2a2a')
        
        # Balls
        for ball in self.balls:
            if ball['hand'] == 0:
                x = 75 + (3 - ball['pos']) * 20
            else:
                x = w - 75 - (3 - ball['pos']) * 20
            y = center_y - 30 + ball['pos'] * 15
            
            display.circle(x, y, 8, fill='#2a2a2a')
    
    def _draw_fire(self, display: Display):
        """Draw Fire game."""
        w = display.width
        h = display.height
        
        # Building
        display.rect(20, self.ui.STATUS_BAR_HEIGHT + 50, 60, 150, fill='#5a5a5a')
        
        # Windows with people
        for f in self.fallers:
            wx = 30 + f['x'] * 20
            wy = self.ui.STATUS_BAR_HEIGHT + 60 + int(f['y']) * 30
            display.rect(wx, wy, 15, 20, fill='#ffaa00')
            display.text(wx + 7, wy + 10, "🧑", '#2a2a2a', 10, 'mm')
        
        # Catchers
        catcher_x = 100 + self.catcher_pos * 40
        catcher_y = h - 60
        display.rect(catcher_x - 20, catcher_y, 40, 10, fill='#2a2a2a')
        display.text(catcher_x - 10, catcher_y + 15, "👨‍🚒", '#2a2a2a', 12)
        display.text(catcher_x + 10, catcher_y + 15, "👨‍🚒", '#2a2a2a', 12)
        
        # Ambulance
        display.text(w - 50, h - 50, "🚑", '#2a2a2a', 24)
    
    def _draw_octopus(self, display: Display):
        """Draw Octopus game."""
        w = display.width
        h = display.height
        
        # Ocean
        display.rect(0, self.ui.STATUS_BAR_HEIGHT + 40, w, h - self.ui.STATUS_BAR_HEIGHT - 40,
                    fill='#6a8b9c')
        
        # Boat (safe zone)
        display.rect(10, self.ui.STATUS_BAR_HEIGHT + 60, 40, 30, fill='#8b4513')
        
        # Treasure
        display.text(w - 40, h - 50, "💰", '#ffff00', 24)
        
        # Tentacles
        for t in self.tentacles:
            tx = int(40 + t * 40)
            display.text(tx, h - 80, "🦑", '#8b008b', 20)
        
        # Diver
        diver_x = 30 + self.diver_pos * 45
        diver_y = h - 100
        display.text(diver_x, diver_y, "🤿", '#2a2a2a', 20)
        
        if self.diver_has_treasure:
            display.text(diver_x + 15, diver_y + 5, "💎", '#00ffff', 12)

