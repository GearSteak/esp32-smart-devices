"""
Tic-Tac-Toe Game
Classic 3x3 grid game against computer.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class TicTacToeApp(App):
    """Tic-Tac-Toe game with AI."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='tictactoe',
            name='Tic-Tac-Toe',
            icon='❌',
            color='#e74c3c'
        )
        
        self.board = []
        self.cursor = [0, 0]
        self.player_turn = True
        self.game_over = False
        self.winner = None
        self.player_score = 0
        self.cpu_score = 0
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.cursor = [1, 1]
        self.player_turn = True
        self.game_over = False
        self.winner = None
    
    def _check_winner(self) -> str:
        """Check for a winner. Returns 'X', 'O', 'tie', or ''."""
        # Rows
        for row in self.board:
            if row[0] == row[1] == row[2] != '':
                return row[0]
        
        # Columns
        for c in range(3):
            if self.board[0][c] == self.board[1][c] == self.board[2][c] != '':
                return self.board[0][c]
        
        # Diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return self.board[0][2]
        
        # Tie?
        if all(self.board[r][c] != '' for r in range(3) for c in range(3)):
            return 'tie'
        
        return ''
    
    def _ai_move(self):
        """Simple AI: try to win, block, or random."""
        # Try to win
        for r in range(3):
            for c in range(3):
                if self.board[r][c] == '':
                    self.board[r][c] = 'O'
                    if self._check_winner() == 'O':
                        return
                    self.board[r][c] = ''
        
        # Block player
        for r in range(3):
            for c in range(3):
                if self.board[r][c] == '':
                    self.board[r][c] = 'X'
                    if self._check_winner() == 'X':
                        self.board[r][c] = 'O'
                        return
                    self.board[r][c] = ''
        
        # Take center
        if self.board[1][1] == '':
            self.board[1][1] = 'O'
            return
        
        # Take corner
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        random.shuffle(corners)
        for r, c in corners:
            if self.board[r][c] == '':
                self.board[r][c] = 'O'
                return
        
        # Take any
        for r in range(3):
            for c in range(3):
                if self.board[r][c] == '':
                    self.board[r][c] = 'O'
                    return
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if not self.player_turn:
            return True
        
        if event.code == KeyCode.UP:
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif event.code == KeyCode.DOWN:
            self.cursor[0] = min(2, self.cursor[0] + 1)
        elif event.code == KeyCode.LEFT:
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif event.code == KeyCode.RIGHT:
            self.cursor[1] = min(2, self.cursor[1] + 1)
        elif event.code == KeyCode.ENTER:
            r, c = self.cursor
            if self.board[r][c] == '':
                self.board[r][c] = 'X'
                
                winner = self._check_winner()
                if winner:
                    self.game_over = True
                    self.winner = winner
                    if winner == 'X':
                        self.player_score += 1
                    elif winner == 'O':
                        self.cpu_score += 1
                else:
                    self.player_turn = False
                    self._ai_move()
                    
                    winner = self._check_winner()
                    if winner:
                        self.game_over = True
                        self.winner = winner
                        if winner == 'O':
                            self.cpu_score += 1
                    else:
                        self.player_turn = True
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Score
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 15, 
                    f"You(X): {self.player_score}", 'white', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 15,
                    f"CPU(O): {self.cpu_score}", 'white', 12, 'rt')
        
        cell_size = 60
        grid_size = cell_size * 3
        offset_x = (display.width - grid_size) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 45
        
        # Grid lines
        for i in range(1, 3):
            display.rect(offset_x + i * cell_size - 1, offset_y, 2, grid_size, fill='#ffffff')
            display.rect(offset_x, offset_y + i * cell_size - 1, grid_size, 2, fill='#ffffff')
        
        # Cells
        for r in range(3):
            for c in range(3):
                x = offset_x + c * cell_size + cell_size // 2
                y = offset_y + r * cell_size + cell_size // 2
                
                is_cursor = (r == self.cursor[0] and c == self.cursor[1])
                
                if is_cursor and not self.game_over:
                    display.rect(offset_x + c * cell_size + 5, offset_y + r * cell_size + 5,
                               cell_size - 10, cell_size - 10, fill='#333366')
                
                if self.board[r][c] == 'X':
                    display.text(x, y, '❌', '#ff0000', 28, 'mm')
                elif self.board[r][c] == 'O':
                    display.text(x, y, '⭕', '#0088ff', 28, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 + 50, display.width - 60, 45,
                        fill='#000000', outline='white')
            if self.winner == 'X':
                msg = "🎉 YOU WIN!"
                color = '#00ff00'
            elif self.winner == 'O':
                msg = "CPU WINS!"
                color = '#ff0000'
            else:
                msg = "IT'S A TIE!"
                color = '#ffff00'
            
            display.text(display.width // 2, display.height // 2 + 72,
                        msg, color, 14, 'mm')

