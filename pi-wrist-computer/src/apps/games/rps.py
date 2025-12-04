"""
Rock Paper Scissors Game
Classic hand game against computer.
"""

import random
import time
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class RPSApp(App):
    """Rock Paper Scissors game."""
    
    CHOICES = ['rock', 'paper', 'scissors']
    ICONS = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
    WINS = {'rock': 'scissors', 'paper': 'rock', 'scissors': 'paper'}
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='rps',
            name='RPS',
            icon='✊',
            color='#e67e22'
        )
        
        self.player_choice = None
        self.cpu_choice = None
        self.result = None
        self.player_score = 0
        self.cpu_score = 0
        self.selected = 0
        self.showing_result = False
        self.result_time = 0
    
    def on_enter(self):
        self._reset_round()
    
    def on_exit(self):
        pass
        self.player_score = 0
        self.cpu_score = 0
    
    def _reset_round(self):
        """Reset for new round."""
        self.player_choice = None
        self.cpu_choice = None
        self.result = None
        self.selected = 0
        self.showing_result = False
    
    def _play(self, choice: str):
        """Play a round."""
        self.player_choice = choice
        self.cpu_choice = random.choice(self.CHOICES)
        
        if self.player_choice == self.cpu_choice:
            self.result = 'tie'
        elif self.WINS[self.player_choice] == self.cpu_choice:
            self.result = 'win'
            self.player_score += 1
        else:
            self.result = 'lose'
            self.cpu_score += 1
        
        self.showing_result = True
        self.result_time = time.time()
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.showing_result:
            if time.time() - self.result_time > 1.5 or event.code == KeyCode.ENTER:
                self._reset_round()
            return True
        
        if event.code == KeyCode.LEFT:
            self.selected = (self.selected - 1) % 3
        elif event.code == KeyCode.RIGHT:
            self.selected = (self.selected + 1) % 3
        elif event.code == KeyCode.ENTER:
            self._play(self.CHOICES[self.selected])
        elif event.char == 'r' or event.char == 'R':
            self._play('rock')
        elif event.char == 'p' or event.char == 'P':
            self._play('paper')
        elif event.char == 's' or event.char == 'S':
            self._play('scissors')
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Score
        display.text(display.width // 4, self.ui.STATUS_BAR_HEIGHT + 25,
                    f"You: {self.player_score}", 'white', 14, 'mm')
        display.text(3 * display.width // 4, self.ui.STATUS_BAR_HEIGHT + 25,
                    f"CPU: {self.cpu_score}", 'white', 14, 'mm')
        
        center_y = display.height // 2
        
        if self.showing_result:
            # Show result
            display.text(display.width // 4, center_y - 20,
                        self.ICONS[self.player_choice], 'white', 48, 'mm')
            display.text(display.width // 2, center_y - 20, "VS", '#888888', 14, 'mm')
            display.text(3 * display.width // 4, center_y - 20,
                        self.ICONS[self.cpu_choice], 'white', 48, 'mm')
            
            result_colors = {'win': '#00ff00', 'lose': '#ff0000', 'tie': '#ffff00'}
            result_text = {'win': 'YOU WIN!', 'lose': 'YOU LOSE!', 'tie': "IT'S A TIE!"}
            
            display.text(display.width // 2, center_y + 50,
                        result_text[self.result], result_colors[self.result], 20, 'mm')
        else:
            # Selection
            display.text(display.width // 2, center_y - 40,
                        "Choose:", '#888888', 14, 'mm')
            
            x_positions = [display.width // 4, display.width // 2, 3 * display.width // 4]
            
            for i, choice in enumerate(self.CHOICES):
                x = x_positions[i]
                selected = (i == self.selected)
                
                if selected:
                    display.circle(x, center_y + 10, 35, fill='#0066cc')
                
                display.text(x, center_y + 10, self.ICONS[choice], 'white', 36, 'mm')
                display.text(x, center_y + 50, choice.upper()[:1], 
                           '#ffff00' if selected else '#666666', 12, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 15,
                    "←→:Select ⏎:Play  R/P/S:Quick", '#555555', 9, 'mm')

