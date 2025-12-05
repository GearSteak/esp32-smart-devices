"""
Checkers Game
Classic board game with simple AI.
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class CheckersApp(App):
    """Checkers board game."""
    
    SIZE = 8
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='checkers',
            name='Checkers',
            icon='🔴',
            color='#c0392b'
        )
        
        self.board = []
        self.cursor = [0, 0]
        self.selected = None
        self.valid_moves = []
        self.player_turn = True
        self.game_over = False
        self.winner = None
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Setup new game."""
        self.board = [[None] * self.SIZE for _ in range(self.SIZE)]
        
        # Place pieces
        for row in range(3):
            for col in range(self.SIZE):
                if (row + col) % 2 == 1:
                    self.board[row][col] = ('black', False)  # (color, is_king)
        
        for row in range(5, 8):
            for col in range(self.SIZE):
                if (row + col) % 2 == 1:
                    self.board[row][col] = ('red', False)
        
        self.cursor = [5, 0]
        self.selected = None
        self.valid_moves = []
        self.player_turn = True
        self.game_over = False
        self.winner = None
    
    def _get_moves(self, row: int, col: int) -> list:
        """Get valid moves for a piece."""
        piece = self.board[row][col]
        if not piece:
            return []
        
        color, is_king = piece
        moves = []
        jumps = []
        
        # Direction based on color
        dirs = []
        if color == 'red' or is_king:
            dirs.extend([(-1, -1), (-1, 1)])
        if color == 'black' or is_king:
            dirs.extend([(1, -1), (1, 1)])
        
        for dr, dc in dirs:
            nr, nc = row + dr, col + dc
            
            # Simple move
            if 0 <= nr < self.SIZE and 0 <= nc < self.SIZE:
                if self.board[nr][nc] is None:
                    moves.append((nr, nc, False))
                elif self.board[nr][nc][0] != color:
                    # Jump
                    jr, jc = nr + dr, nc + dc
                    if 0 <= jr < self.SIZE and 0 <= jc < self.SIZE:
                        if self.board[jr][jc] is None:
                            jumps.append((jr, jc, True))
        
        # Must jump if possible
        return jumps if jumps else moves
    
    def _make_move(self, from_pos: tuple, to_pos: tuple, is_jump: bool):
        """Make a move."""
        fr, fc = from_pos
        tr, tc = to_pos
        
        piece = self.board[fr][fc]
        self.board[tr][tc] = piece
        self.board[fr][fc] = None
        
        if is_jump:
            # Remove jumped piece
            jr, jc = (fr + tr) // 2, (fc + tc) // 2
            self.board[jr][jc] = None
        
        # King promotion
        color, is_king = piece
        if (color == 'red' and tr == 0) or (color == 'black' and tr == 7):
            self.board[tr][tc] = (color, True)
        
        # Check for more jumps
        if is_jump:
            more_jumps = [m for m in self._get_moves(tr, tc) if m[2]]
            if more_jumps:
                self.selected = (tr, tc)
                self.valid_moves = more_jumps
                return False  # Turn continues
        
        return True  # Turn ends
    
    def _ai_move(self):
        """Simple AI move."""
        best_move = None
        best_score = -1000
        
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                piece = self.board[row][col]
                if piece and piece[0] == 'black':
                    moves = self._get_moves(row, col)
                    for move in moves:
                        score = 10 if move[2] else 1  # Prefer jumps
                        if move[0] == 7:  # King row
                            score += 5
                        if score > best_score:
                            best_score = score
                            best_move = ((row, col), move)
        
        if best_move:
            from_pos, (tr, tc, is_jump) = best_move
            turn_ends = self._make_move(from_pos, (tr, tc), is_jump)
            if not turn_ends:
                self._ai_move()  # Continue if more jumps
    
    def _check_game_over(self):
        """Check if game is over."""
        red_pieces = black_pieces = 0
        red_moves = black_moves = False
        
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                piece = self.board[row][col]
                if piece:
                    if piece[0] == 'red':
                        red_pieces += 1
                        if self._get_moves(row, col):
                            red_moves = True
                    else:
                        black_pieces += 1
                        if self._get_moves(row, col):
                            black_moves = True
        
        if red_pieces == 0 or not red_moves:
            self.game_over = True
            self.winner = 'black'
        elif black_pieces == 0 or not black_moves:
            self.game_over = True
            self.winner = 'red'
    
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
            self.cursor[0] = min(self.SIZE - 1, self.cursor[0] + 1)
        elif event.code == KeyCode.LEFT:
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif event.code == KeyCode.RIGHT:
            self.cursor[1] = min(self.SIZE - 1, self.cursor[1] + 1)
        elif event.code == KeyCode.ENTER:
            row, col = self.cursor
            
            if self.selected:
                # Try to move to selected position
                for mr, mc, is_jump in self.valid_moves:
                    if (mr, mc) == (row, col):
                        turn_ends = self._make_move(self.selected, (row, col), is_jump)
                        if turn_ends:
                            self.selected = None
                            self.valid_moves = []
                            self._check_game_over()
                            if not self.game_over:
                                self.player_turn = False
                                self._ai_move()
                                self._check_game_over()
                                self.player_turn = True
                        break
                else:
                    # Deselect if clicking elsewhere
                    self.selected = None
                    self.valid_moves = []
            else:
                # Select piece
                piece = self.board[row][col]
                if piece and piece[0] == 'red':
                    moves = self._get_moves(row, col)
                    if moves:
                        self.selected = (row, col)
                        self.valid_moves = moves
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        cell_size = 24  # Reduced for 240px height
        board_size = self.SIZE * cell_size
        offset_x = (display.width - board_size) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 18
        
        for row in range(self.SIZE):
            for col in range(self.SIZE):
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
                elif any((mr, mc) == (row, col) for mr, mc, _ in self.valid_moves):
                    color = '#77ff77'
                elif (row, col) == tuple(self.cursor):
                    color = '#ffff77'
                
                display.rect(x, y, cell_size, cell_size, fill=color)
                
                # Piece
                piece = self.board[row][col]
                if piece:
                    pc, is_king = piece
                    if pc == 'red':
                        display.circle(x + cell_size // 2, y + cell_size // 2, 9, fill='#ff0000')
                    else:
                        display.circle(x + cell_size // 2, y + cell_size // 2, 9, fill='#333333')
                    
                    if is_king:
                        display.text(x + cell_size // 2, y + cell_size // 2, '♔', '#ffff00', 10, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 - 20, display.width - 60, 40,
                        fill='#000000', outline='white')
            msg = "YOU WIN!" if self.winner == 'red' else "CPU WINS"
            color = '#00ff00' if self.winner == 'red' else '#ff0000'
            display.text(display.width // 2, display.height // 2, msg, color, 14, 'mm')

