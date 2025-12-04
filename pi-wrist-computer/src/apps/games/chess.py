"""
Chess Game
Classic chess with simple AI.
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class ChessApp(App):
    """Chess game with basic AI."""
    
    PIECES = {
        'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
        'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
    }
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='chess',
            name='Chess',
            icon='♟',
            color='#f0d9b5'
        )
        
        self.board = []
        self.cursor = [7, 4]
        self.selected = None
        self.valid_moves = []
        self.white_turn = True
        self.game_over = False
        self.winner = None
        self.message = ""
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Setup new game."""
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
        ]
        self.cursor = [7, 4]
        self.selected = None
        self.valid_moves = []
        self.white_turn = True
        self.game_over = False
        self.winner = None
        self.message = ""
    
    def _is_white(self, piece: str) -> bool:
        """Check if piece is white."""
        return piece.isupper()
    
    def _get_moves(self, row: int, col: int) -> list:
        """Get valid moves for a piece (simplified)."""
        piece = self.board[row][col]
        if piece == '.':
            return []
        
        moves = []
        is_white = self._is_white(piece)
        p = piece.lower()
        
        def add_if_valid(r, c, capture_only=False, move_only=False):
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.':
                    if not capture_only:
                        moves.append((r, c))
                    return True
                elif self._is_white(target) != is_white:
                    if not move_only:
                        moves.append((r, c))
                    return False
                return False
            return False
        
        def add_line(dr, dc):
            for i in range(1, 8):
                if not add_if_valid(row + dr * i, col + dc * i):
                    break
        
        if p == 'p':  # Pawn
            dir = -1 if is_white else 1
            start_row = 6 if is_white else 1
            
            add_if_valid(row + dir, col, move_only=True)
            if row == start_row and self.board[row + dir][col] == '.':
                add_if_valid(row + dir * 2, col, move_only=True)
            add_if_valid(row + dir, col - 1, capture_only=True)
            add_if_valid(row + dir, col + 1, capture_only=True)
        
        elif p == 'n':  # Knight
            for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                          (1, -2), (1, 2), (2, -1), (2, 1)]:
                add_if_valid(row + dr, col + dc)
        
        elif p == 'b':  # Bishop
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                add_line(dr, dc)
        
        elif p == 'r':  # Rook
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                add_line(dr, dc)
        
        elif p == 'q':  # Queen
            for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                          (0, 1), (1, -1), (1, 0), (1, 1)]:
                add_line(dr, dc)
        
        elif p == 'k':  # King
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr or dc:
                        add_if_valid(row + dr, col + dc)
        
        return moves
    
    def _make_move(self, from_pos: tuple, to_pos: tuple):
        """Make a move."""
        fr, fc = from_pos
        tr, tc = to_pos
        
        captured = self.board[tr][tc]
        self.board[tr][tc] = self.board[fr][fc]
        self.board[fr][fc] = '.'
        
        # Pawn promotion
        piece = self.board[tr][tc]
        if piece == 'P' and tr == 0:
            self.board[tr][tc] = 'Q'
        elif piece == 'p' and tr == 7:
            self.board[tr][tc] = 'q'
        
        # Check for king capture (simplified win condition)
        if captured.lower() == 'k':
            self.game_over = True
            self.winner = 'White' if self._is_white(self.board[tr][tc]) else 'Black'
    
    def _ai_move(self):
        """Simple AI: random valid move with capture preference."""
        import random
        
        all_moves = []
        captures = []
        
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece != '.' and not self._is_white(piece):
                    moves = self._get_moves(r, c)
                    for mr, mc in moves:
                        move = ((r, c), (mr, mc))
                        all_moves.append(move)
                        if self.board[mr][mc] != '.':
                            captures.append(move)
        
        if captures:
            from_pos, to_pos = random.choice(captures)
        elif all_moves:
            from_pos, to_pos = random.choice(all_moves)
        else:
            self.game_over = True
            self.winner = 'White'
            return
        
        self._make_move(from_pos, to_pos)
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if not self.white_turn:
            return True
        
        if event.code == KeyCode.UP:
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif event.code == KeyCode.DOWN:
            self.cursor[0] = min(7, self.cursor[0] + 1)
        elif event.code == KeyCode.LEFT:
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif event.code == KeyCode.RIGHT:
            self.cursor[1] = min(7, self.cursor[1] + 1)
        elif event.code == KeyCode.ENTER:
            row, col = self.cursor
            
            if self.selected:
                if (row, col) in self.valid_moves:
                    self._make_move(self.selected, (row, col))
                    self.selected = None
                    self.valid_moves = []
                    
                    if not self.game_over:
                        self.white_turn = False
                        self._ai_move()
                        self.white_turn = True
                else:
                    self.selected = None
                    self.valid_moves = []
            else:
                piece = self.board[row][col]
                if piece != '.' and self._is_white(piece):
                    self.selected = (row, col)
                    self.valid_moves = self._get_moves(row, col)
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        cell_size = 28
        board_size = 8 * cell_size
        offset_x = (display.width - board_size) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 20
        
        for row in range(8):
            for col in range(8):
                x = offset_x + col * cell_size
                y = offset_y + row * cell_size
                
                # Square color
                if (row + col) % 2 == 0:
                    color = '#f0d9b5'
                else:
                    color = '#b58863'
                
                # Highlight
                if self.selected == (row, col):
                    color = '#7777ff'
                elif (row, col) in self.valid_moves:
                    color = '#77ff77'
                elif [row, col] == self.cursor:
                    color = '#ffff77'
                
                display.rect(x, y, cell_size, cell_size, fill=color)
                
                # Piece
                piece = self.board[row][col]
                if piece != '.':
                    symbol = self.PIECES.get(piece, '?')
                    pcolor = '#ffffff' if self._is_white(piece) else '#000000'
                    display.text(x + cell_size // 2, y + cell_size // 2,
                               symbol, pcolor, 18, 'mm')
        
        # Turn indicator
        turn = "White" if self.white_turn else "Black"
        display.text(display.width // 2, display.height - 15,
                    f"{turn}'s turn", '#888888', 10, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 - 20, display.width - 60, 40,
                        fill='#000000', outline='white')
            msg = f"{self.winner} wins!"
            color = '#00ff00' if self.winner == 'White' else '#ff0000'
            display.text(display.width // 2, display.height // 2, msg, color, 14, 'mm')

