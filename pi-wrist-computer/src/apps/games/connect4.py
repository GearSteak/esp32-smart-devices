"""
Connect 4 Game
Drop discs to connect four in a row.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class Connect4App(App):
    """Connect 4 game with simple AI."""
    
    ROWS = 6
    COLS = 7
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='connect4',
            name='Connect 4',
            icon='🔴',
            color='#ff0000'
        )
        
        self.board = []
        self.current_col = 3
        self.player_turn = True
        self.game_over = False
        self.winner = None
        self.vs_ai = True
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self.board = [[0] * self.COLS for _ in range(self.ROWS)]
        self.current_col = 3
        self.player_turn = True
        self.game_over = False
        self.winner = None
    
    def _drop_disc(self, col: int, player: int) -> int:
        """Drop a disc in a column. Returns row or -1 if full."""
        for row in range(self.ROWS - 1, -1, -1):
            if self.board[row][col] == 0:
                self.board[row][col] = player
                return row
        return -1
    
    def _check_win(self, player: int) -> bool:
        """Check if player has won."""
        # Horizontal
        for row in range(self.ROWS):
            for col in range(self.COLS - 3):
                if all(self.board[row][col + i] == player for i in range(4)):
                    return True
        
        # Vertical
        for row in range(self.ROWS - 3):
            for col in range(self.COLS):
                if all(self.board[row + i][col] == player for i in range(4)):
                    return True
        
        # Diagonal (positive slope)
        for row in range(self.ROWS - 3):
            for col in range(self.COLS - 3):
                if all(self.board[row + i][col + i] == player for i in range(4)):
                    return True
        
        # Diagonal (negative slope)
        for row in range(3, self.ROWS):
            for col in range(self.COLS - 3):
                if all(self.board[row - i][col + i] == player for i in range(4)):
                    return True
        
        return False
    
    def _is_draw(self) -> bool:
        """Check if game is a draw."""
        return all(self.board[0][col] != 0 for col in range(self.COLS))
    
    def _ai_move(self):
        """Simple AI makes a move."""
        # Try to win
        for col in range(self.COLS):
            if self.board[0][col] == 0:
                row = self._find_row(col)
                if row >= 0:
                    self.board[row][col] = 2
                    if self._check_win(2):
                        self.board[row][col] = 0
                        return col
                    self.board[row][col] = 0
        
        # Block player
        for col in range(self.COLS):
            if self.board[0][col] == 0:
                row = self._find_row(col)
                if row >= 0:
                    self.board[row][col] = 1
                    if self._check_win(1):
                        self.board[row][col] = 0
                        return col
                    self.board[row][col] = 0
        
        # Prefer center
        if self.board[0][3] == 0:
            return 3
        
        # Random valid move
        valid = [col for col in range(self.COLS) if self.board[0][col] == 0]
        return random.choice(valid) if valid else -1
    
    def _find_row(self, col: int) -> int:
        """Find the row where a disc would land."""
        for row in range(self.ROWS - 1, -1, -1):
            if self.board[row][col] == 0:
                return row
        return -1
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if not self.player_turn and self.vs_ai:
            return True
        
        if event.code == KeyCode.LEFT:
            self.current_col = max(0, self.current_col - 1)
        elif event.code == KeyCode.RIGHT:
            self.current_col = min(self.COLS - 1, self.current_col + 1)
        elif event.code == KeyCode.ENTER:
            player = 1 if self.player_turn else 2
            if self._drop_disc(self.current_col, player) >= 0:
                if self._check_win(player):
                    self.winner = player
                    self.game_over = True
                elif self._is_draw():
                    self.game_over = True
                else:
                    self.player_turn = not self.player_turn
                    
                    # AI move
                    if self.vs_ai and not self.player_turn and not self.game_over:
                        ai_col = self._ai_move()
                        if ai_col >= 0:
                            self._drop_disc(ai_col, 2)
                            if self._check_win(2):
                                self.winner = 2
                                self.game_over = True
                            elif self._is_draw():
                                self.game_over = True
                            else:
                                self.player_turn = True
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        cell_size = 30
        grid_width = self.COLS * cell_size
        grid_height = self.ROWS * cell_size
        offset_x = (display.width - grid_width) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 45
        
        # Turn indicator / preview
        preview_y = self.ui.STATUS_BAR_HEIGHT + 20
        if not self.game_over:
            color = '#ff0000' if self.player_turn else '#ffff00'
            x = offset_x + self.current_col * cell_size + cell_size // 2
            display.circle(x, preview_y, 10, fill=color)
        
        # Board background
        display.rect(offset_x - 5, offset_y - 5, grid_width + 10, grid_height + 10, fill='#0000aa')
        
        # Cells
        for row in range(self.ROWS):
            for col in range(self.COLS):
                x = offset_x + col * cell_size + cell_size // 2
                y = offset_y + row * cell_size + cell_size // 2
                
                cell = self.board[row][col]
                if cell == 0:
                    color = '#1a1a1a'
                elif cell == 1:
                    color = '#ff0000'
                else:
                    color = '#ffff00'
                
                display.circle(x, y, 12, fill=color)
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 - 25, display.width - 60, 50,
                        fill='#000000', outline='white')
            if self.winner:
                if self.winner == 1:
                    msg = "🔴 RED WINS!"
                else:
                    msg = "🟡 YELLOW WINS!"
                display.text(display.width // 2, display.height // 2,
                            msg, 'white', 14, 'mm')
            else:
                display.text(display.width // 2, display.height // 2,
                            "DRAW!", '#888888', 14, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 10,
                    "←→:Move ⏎:Drop", '#555555', 9, 'mm')

