import pygame
import sys
import json
import os
import pickle
import logging
import time # Added for message timer
import random # Added for random taunt selection

# --- Constants ---
WIDTH, HEIGHT = 650, 650
ROWS, COLS = 5, 5
SQUARE_SIZE = WIDTH // COLS

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 168, 82)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
YELLOW = (255, 223, 0)
SKY_BLUE = (135, 206, 235)
GREY = (128, 128, 128)
ORANGE = (255, 165, 0)
AI_MESSAGE_COLOR = (255, 100, 100) # A reddish color for taunts

# Piece Symbols
EMPTY = '.'
KING = 'K'
KNIGHT = 'N'

# Movesets
knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)]
king_moves = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
              (0, 1), (1, -1), (1, 0), (1, 1)]

# Safe Zones
safe_zones = []

# --- AI Taunt Messages ---
AI_TAUNTS = [
    "Is that all you've got?",
    "A lucky shot... won't happen again.",
    "My knights are many, your moves are few.",
    "Did that make you feel better, your majesty?",
    "Impressive... for a king.",
    "Don't get cocky.",
    "I sacrifice knights... strategically!",
    "You merely delay the inevitable.",
    "One down. How many more can you handle?",
    "My calculations account for minor setbacks.",
    "A futile gesture.",
    "My network learns from your 'success'.",
    "Error in calculation... or was it?",
    "That piece was expendable.",
    "Proceed. My traps await.",
]

# --- Setup Logging ---
logging.basicConfig(filename='game_log.txt', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Asset Loading ---
def load_images(size):
    try:
        king_img = pygame.image.load("King.png").convert_alpha()
        knight_img = pygame.image.load("knight.png").convert_alpha()
        king_img = pygame.transform.scale(king_img, (size - 10, size - 10))
        knight_img = pygame.transform.scale(knight_img, (size - 10, size - 10))
        logging.info("Images loaded successfully.")
        return king_img, knight_img
    except pygame.error as e:
        logging.error(f"Error loading images: {e}")
        king_img = pygame.Surface((size - 10, size - 10)); king_img.fill(RED)
        knight_img = pygame.Surface((size - 10, size - 10)); knight_img.fill(BLUE)
        return king_img, knight_img
    except Exception as e:
        logging.critical(f"Unexpected error loading images: {e}")
        raise

# --- Game Class ---
class Game:
    def __init__(self, win, game_mode):
        self.win = win
        self.game_mode = game_mode
        self.board = self.create_board()
        self.king_img, self.knight_img = load_images(SQUARE_SIZE)
        self.reset_game_state()

    def reset_game_state(self):
        """Resets variables for a new game, maintaining game_mode."""
        self.board = self.create_board()
        self.king_pos = self._find_king()
        self.player_turn = 1
        self.selected_piece_pos = None
        self.possible_moves = []
        self.game_over = False
        self.winner = 0
        self.king_kills = 0
        self.turn_count = 1
        self.move_history = []
        self.player1_time = 300
        self.player2_time = 300
        self.king_charge_cooldown = 0
        self.king_escape_available = True
        self.ai_thinking = False
        # --- State for AI messages ---
        self.ai_message = None
        self.ai_message_timer = 0
        self.ai_message_duration = 3.5 # Seconds the message stays on screen
        # --- End AI message state ---
        logging.info(f"Game state reset. Mode: {self.game_mode}")

    def create_board(self):
        """Initializes the game board."""
        # --- Unchanged ---
        board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        board[ROWS // 2][COLS // 2] = KING
        knights = [(0, 0), (0, COLS - 1), (ROWS - 1, 0), (ROWS - 1, COLS - 1)]
        for r, c in knights:
            if 0 <= r < ROWS and 0 <= c < COLS:
                board[r][c] = KNIGHT
        return board

    def _find_king(self):
        """Finds the initial king position."""
        # --- Unchanged ---
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == KING:
                    return (r, c)
        logging.error("King not found on initial board setup!")
        return (ROWS // 2, COLS // 2)

    def draw(self):
        """Draws the entire game state, including AI messages."""
        self.win.fill(BLUE)
        pygame.draw.rect(self.win, YELLOW, (0, 0, WIDTH, HEIGHT), 5)

        # Highlight safe zones lightly
        for r, c in safe_zones:
             rect = pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
             pygame.draw.rect(self.win, (240, 240, 100), rect, 2)

        king_in_check = self.is_square_under_attack(self.king_pos[0], self.king_pos[1]) if self.king_pos else False

        # Draw board squares and pieces
        for row in range(ROWS):
            for col in range(COLS):
                rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                is_selected = self.selected_piece_pos == (row, col)
                is_possible_move = (row, col) in self.possible_moves
                is_king_square_and_check = (row, col) == self.king_pos and king_in_check
                is_king_square_and_game_over = self.game_over and self.board[row][col] == KING

                if is_king_square_and_game_over or (is_king_square_and_check and not self.game_over): color = RED
                elif is_selected: color = GREEN
                elif is_possible_move: color = SKY_BLUE
                else: color = BLACK if (row + col) % 2 == 0 else WHITE
                pygame.draw.rect(self.win, color, rect)

                piece = self.board[row][col]
                if piece == KING: self.win.blit(self.king_img, (rect.x + 5, rect.y + 5))
                elif piece == KNIGHT: self.win.blit(self.knight_img, (rect.x + 5, rect.y + 5))

        # Draw Turn Indicator
        self.draw_turn_indicator()

        # Draw AI Thinking message
        if self.ai_thinking:
             font = pygame.font.Font(None, 36)
             ai_text = font.render("AI Thinking...", True, ORANGE, BLACK)
             ai_rect = ai_text.get_rect(center=(WIDTH // 2, HEIGHT - 30))
             self.win.blit(ai_text, ai_rect)

        # --- Draw AI Taunt Message ---
        if self.ai_message and time.time() < self.ai_message_timer:
            font = pygame.font.Font(None, 30) # Slightly smaller font for messages
            message_surface = font.render(self.ai_message, True, AI_MESSAGE_COLOR) # Use defined color
            message_rect = message_surface.get_rect(center=(WIDTH // 2, HEIGHT - 65)) # Position above AI thinking text

            # Optional: Add a semi-transparent background for readability
            bg_rect = message_rect.inflate(10, 5)
            bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 150)) # Black background, semi-transparent
            self.win.blit(bg_surface, bg_rect.topleft)

            self.win.blit(message_surface, message_rect)
        elif self.ai_message and time.time() >= self.ai_message_timer:
            self.ai_message = None # Clear message after timer expires
        # --- End AI Taunt Message Drawing ---

        # Draw Game Over screen if applicable
        if self.game_over:
            self.display_game_over()

        pygame.display.update()

    def draw_turn_indicator(self):
        """Draws the turn indicator text, including AI status."""
        # --- Unchanged ---
        font = pygame.font.Font(None, 28)
        player_text = ""
        if self.player_turn == 1: player_text = "King (Player 1)"
        elif self.player_turn == 2: player_text = "Knights (AI)" if self.game_mode == 'pva' else "Knights (Player 2)"
        text = f"Turn: {self.turn_count} | {player_text} to move"
        indicator_surface = font.render(text, True, BLACK, YELLOW)
        indicator_rect = indicator_surface.get_rect(center=(WIDTH // 2, SQUARE_SIZE // 3))
        self.win.blit(indicator_surface, indicator_rect)
        font_small = pygame.font.Font(None, 20)
        charge_cd_text = f"Charge CD: {self.king_charge_cooldown}" if self.king_charge_cooldown > 0 else "Charge Ready (C)"
        escape_text = "Escape Available (E)" if self.king_escape_available else "Escape Used"
        charge_surf = font_small.render(charge_cd_text, True, WHITE); escape_surf = font_small.render(escape_text, True, WHITE)
        self.win.blit(charge_surf, (10, HEIGHT - 45)); self.win.blit(escape_surf, (10, HEIGHT - 25))

    def is_square_under_attack(self, r, c):
        """Checks if a square (r, c) is attacked by any knight."""
        # --- Unchanged ---
        for dr, dc in knight_moves:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == KNIGHT: return True
        return False

    def get_valid_moves(self, r, c):
        """Gets valid moves for the piece at (r, c)."""
        # --- Unchanged ---
        if not (0 <= r < ROWS and 0 <= c < COLS): return []
        piece = self.board[r][c]; moves = []
        if piece == KING: current_moves = king_moves
        elif piece == KNIGHT: current_moves = knight_moves
        else: return []
        for dr, dc in current_moves:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                target_content = self.board[nr][nc]
                if piece == KING:
                    if target_content in [EMPTY, KNIGHT] and not self.is_square_under_attack(nr, nc): moves.append((nr, nc))
                elif piece == KNIGHT:
                    if target_content == EMPTY: moves.append((nr, nc))
        return moves

    def select_piece(self, row, col):
        """Handles selecting a piece. Returns True if selection successful."""
        # --- Unchanged ---
        if self.ai_thinking or (self.game_mode == 'pva' and self.player_turn == 2): return False
        if 0 <= row < ROWS and 0 <= col < COLS:
            piece = self.board[row][col]
            if (self.player_turn == 1 and piece == KING) or (self.player_turn == 2 and piece == KNIGHT):
                self.selected_piece_pos = (row, col); self.possible_moves = self.get_valid_moves(row, col)
                logging.info(f"Player {self.player_turn} selected piece at ({row}, {col}). Possible moves: {self.possible_moves}")
                return True
        self.selected_piece_pos = None; self.possible_moves = []; return False

    def attempt_move(self, end_row, end_col):
        """Attempts to move the selected piece to (end_row, end_col). Returns True if move successful."""
        if self.selected_piece_pos is None:
            logging.warning("Attempt move called with no piece selected.")
            return False

        start_row, start_col = self.selected_piece_pos
        piece_moved = self.board[start_row][start_col]

        if (end_row, end_col) not in self.get_valid_moves(start_row, start_col):
            logging.warning(f"Invalid move destination ({end_row}, {end_col}) attempted for piece at {self.selected_piece_pos}")
            self.selected_piece_pos = None; self.possible_moves = []; return False

        # Record state for Undo
        board_state_before_move = [row[:] for row in self.board]
        move_info = { "start_pos": (start_row, start_col), "end_pos": (end_row, end_col),
                      "piece_moved": piece_moved, "piece_captured": self.board[end_row][end_col],
                      "king_kills_before": self.king_kills, "player_turn_before": self.player_turn,
                      "king_pos_before": self.king_pos, "turn_count_before": self.turn_count,
                      "board_state": board_state_before_move, "charge_cd_before": self.king_charge_cooldown,
                      "escape_avail_before": self.king_escape_available }
        self.move_history.append(move_info)

        # Execute Move
        target_content = self.board[end_row][end_col]

        if piece_moved == KING and target_content == KNIGHT:
            self.king_kills += 1
            logging.info(f"King captured knight at ({end_row}, {end_col}). Total kills: {self.king_kills}")
            # --- Trigger AI Taunt ---
            if self.game_mode == 'pva':
                self.ai_message = random.choice(AI_TAUNTS)
                self.ai_message_timer = time.time() + self.ai_message_duration
                logging.info(f"AI displayed taunt: {self.ai_message}")
            # --- End AI Taunt Trigger ---

        self.board[start_row][start_col] = EMPTY
        self.board[end_row][end_col] = piece_moved
        if piece_moved == KING: self.king_pos = (end_row, end_col)
        if self.player_turn == 1 and self.king_charge_cooldown > 0: self.king_charge_cooldown -= 1

        self.switch_turn()
        self.check_game_over()
        self.selected_piece_pos = None; self.possible_moves = []; return True

    def switch_turn(self):
        """Switches the player turn and increments turn count."""
        # --- Unchanged ---
        if self.player_turn == 2: self.turn_count += 1
        self.player_turn = 3 - self.player_turn
        logging.info(f"Turn switched to Player {self.player_turn}. Turn count: {self.turn_count}")

    def check_game_over(self):
        """Checks win/loss conditions and updates game state."""
        # --- Game over checks ---
        king_pos = self.king_pos
        knight_positions = self.get_piece_positions(KNIGHT)
        if not king_pos:
            logging.error("King position is invalid/None during game over check.")
            self.winner = 2
            self.game_over = True
            return
        kx, ky = king_pos

        # 1. King reaches safe zone
        if king_pos in safe_zones:
            self.winner = 1
            self.game_over = True
            logging.info("Game Over: King reached a safe zone.")
            return

        # 2. King captures enough knights (MODIFIED - now requires 5 kills, not 4)
        if self.king_kills >=3:  # Increased from
            self.winner = 1
            self.game_over = True
            logging.info(f"Game Over: King captured {self.king_kills} knights (5 or more).")
            return

        # 3. All knights are captured
        if not knight_positions:
            self.winner = 1
            self.game_over = True
            logging.info("Game Over: All knights captured.")
            return

        # --- Knight win conditions follow ---
        # 4. King is surrounded (MODIFIED - now only needs 3 knights, not 4)
        surrounding_knights = 0
        for dr, dc in knight_moves:
            nr, nc = kx + dr, ky + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == KNIGHT:
                surrounding_knights += 1
        if surrounding_knights >= 3:  # Reduced from 4 to 3
            self.winner = 2
            self.game_over = True
            logging.info(f"Game Over: King surrounded by {surrounding_knights} knights.")
            return

        # 5. King has no valid moves
        king_valid_moves = self.get_valid_moves(kx, ky)
        if not king_valid_moves:
            self.winner = 2
            self.game_over = True
            logging.info("Game Over: King has no valid moves.")
            return

        # 6. NEW CONDITION: If game reaches 30 turns, knights win (siege victory)
        if self.turn_count >= 30:
            self.winner = 2
            self.game_over = True
            logging.info("Game Over: Knights win by siege (30 turns reached).")
            return

        # Game continues
        self.winner = 0
        self.game_over = False

    def get_piece_positions(self, piece_type):
        """Finds all positions of a given piece type."""
        # --- Unchanged ---
        positions = [];
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == piece_type: positions.append((r, c))
        return positions

    def display_game_over(self):
        """Displays the game over message overlay."""
        # --- Unchanged ---
        font = pygame.font.Font(None, 74); winner_text = ""
        if self.winner == 1: winner_text = "King (Player 1) wins!"
        elif self.winner == 2: winner_text = "Knights (AI) win!" if self.game_mode == 'pva' else "Knights (Player 2) win!"
        message = winner_text; text = font.render(message, True, YELLOW); text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180))
        self.win.blit(overlay, (0, 0)); self.win.blit(text, text_rect)
        font_small = pygame.font.Font(None, 36); restart_text = font_small.render("Click to Restart", True, WHITE); restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
        self.win.blit(restart_text, restart_rect)

    def handle_click(self, pos):
        """Handles mouse clicks during the game."""
        # --- Unchanged ---
        if self.ai_thinking or (self.game_mode == 'pva' and self.player_turn == 2): return
        if self.game_over: self.reset_game_state(); return
        col = pos[0] // SQUARE_SIZE; row = pos[1] // SQUARE_SIZE
        if self.selected_piece_pos: self.attempt_move(row, col)
        else: self.select_piece(row, col)

    def handle_keypress(self, event):
        """Handles key presses during the game."""
        # --- Unchanged ---
        if self.ai_thinking: return
        if not self.game_over:
            if event.key == pygame.K_u: self.undo_last_move()
            elif event.key == pygame.K_s: self.save_game_state()
            elif event.key == pygame.K_l: self.load_game_state()
            if self.player_turn == 1:
                if event.key == pygame.K_c: self.activate_royal_charge()
                elif event.key == pygame.K_e: self.activate_royal_escape()

    def undo_last_move(self):
        """Reverts the game state to before the last move."""
        # --- Unchanged ---
        if not self.move_history: logging.warning("Undo attempted but move history empty."); return
        last_move = self.move_history.pop()
        self.board = [row[:] for row in last_move["board_state"]]
        self.king_kills = last_move["king_kills_before"]; self.player_turn = last_move["player_turn_before"]
        self.king_pos = last_move["king_pos_before"]; self.turn_count = last_move["turn_count_before"]
        self.king_charge_cooldown = last_move.get("charge_cd_before", 0); self.king_escape_available = last_move.get("escape_avail_before", True)
        self.selected_piece_pos = None; self.possible_moves = []; self.game_over = False; self.winner = 0
        # Clear any active AI message upon undo
        self.ai_message = None
        logging.info("Undo successful.")

    def save_game_state(self, filename="savegame.pkl"):
        """Saves the current game state to a file, including game mode."""
        # --- Unchanged ---
        game_state = { "board": self.board, "player_turn": self.player_turn, "king_pos": self.king_pos, "king_kills": self.king_kills,
                       "turn_count": self.turn_count, "game_over": self.game_over, "winner": self.winner, "move_history": self.move_history,
                       "player1_time": self.player1_time, "player2_time": self.player2_time, "king_charge_cooldown": self.king_charge_cooldown,
                       "king_escape_available": self.king_escape_available, "game_mode": self.game_mode }
        try:
            with open(filename, "wb") as f: pickle.dump(game_state, f); logging.info(f"Game saved to {filename}")
        except Exception as e: logging.error(f"Error saving game: {e}")

    def load_game_state(self, filename="savegame.pkl"):
        """Loads game state from a file, including game mode."""
        # --- Unchanged ---
        try:
            with open(filename, "rb") as f: game_state = pickle.load(f)
            self.game_mode = game_state.get("game_mode", "pvp"); self.board = game_state.get("board", self.create_board())
            self.player_turn = game_state.get("player_turn", 1); self.king_pos = game_state.get("king_pos", self._find_king())
            self.king_kills = game_state.get("king_kills", 0); self.turn_count = game_state.get("turn_count", 1)
            self.game_over = game_state.get("game_over", False); self.winner = game_state.get("winner", 0)
            self.move_history = game_state.get("move_history", []); self.player1_time = game_state.get("player1_time", 300)
            self.player2_time = game_state.get("player2_time", 300); self.king_charge_cooldown = game_state.get("king_charge_cooldown", 0)
            self.king_escape_available = game_state.get("king_escape_available", True)
            self.selected_piece_pos = None; self.possible_moves = []; self.ai_message = None # Clear message on load
            logging.info(f"Game loaded from {filename}. Mode: {self.game_mode}"); self.draw()
        except FileNotFoundError: logging.error(f"Load failed: {filename} not found.")
        except Exception as e: logging.error(f"Error loading game: {e}")

    # --- AI Logic ---
    def evaluate_board(self):
        """Evaluates the current board state from the Knights' perspective."""
        score = 0
        if not self.king_pos:
            return -1000

        king_r, king_c = self.king_pos
        knight_positions = self.get_piece_positions(KNIGHT)
        king_valid_moves = self.get_valid_moves(king_r, king_c)

        # Heavily penalize having few knights
        score += len(knight_positions) * 15

        # Reward restricting king's movement
        score -= len(king_valid_moves) * 10

        # Reward knights being close to the king
        total_distance = 0
        for kr, kc in knight_positions:
            distance = abs(kr - king_r) + abs(kc - king_c)
            total_distance += distance

            # Reward knights that can attack the king in 1 move
            potential_moves = self.get_valid_moves(kr, kc)
            for pr, pc in potential_moves:
                if abs(pr - king_r) + abs(pc - king_c) <= 2:  # Knight can get close to king
                    score += 5

        # Calculate average distance and reward closeness
        if knight_positions:
            avg_distance = total_distance / len(knight_positions)
            score += (7 - avg_distance) * 8  # Prefer knights closer to king

        # Reward surrounding the king
        surrounding_knights = 0
        for dr, dc in knight_moves:
            nr, nc = king_r + dr, king_c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == KNIGHT:
                surrounding_knights += 1
        score += surrounding_knights * 20  # Heavily reward surrounding

        # Reward knights controlling squares close to safe zones
        for safe_r, safe_c in safe_zones:
            for kr, kc in knight_positions:
                distance_to_safe = abs(kr - safe_r) + abs(kc - safe_c)
                if distance_to_safe <= 2:
                    score += 10  # Reward knights close to safe zones

        # Reward knights blocking paths to safe zones
        king_to_safe_distances = []
        for safe_r, safe_c in safe_zones:
            king_to_safe = abs(king_r - safe_r) + abs(king_c - safe_c)
            king_to_safe_distances.append(king_to_safe)

        # Knights should prioritize blocking the closest safe zone
        min_distance = min(king_to_safe_distances) if king_to_safe_distances else 0
        for kr, kc in knight_positions:
            for safe_r, safe_c in safe_zones:
                safe_distance = abs(safe_r - kr) + abs(safe_c - kc)
                king_to_safe = abs(king_r - safe_r) + abs(king_c - safe_c)
                if king_to_safe == min_distance and safe_distance <= 2:
                    score += 15  # Heavily reward blocking the closest safe zone

        # Reward knights that check the king
        if self.is_square_under_attack(king_r, king_c):
            score += 25

        # Reward progress through the game (Knights win if game drags on)
        score += self.turn_count * 2

        return score

    def ai_make_move(self):
        """Determines and returns the best move for the Knights AI."""
        # --- Unchanged ---
        self.ai_thinking = True; self.draw(); pygame.time.delay(100) # Ensure "Thinking" shows
        best_move = None; best_score = -float('inf'); possible_ai_moves = []
        knight_positions = self.get_piece_positions(KNIGHT)
        for start_pos in knight_positions:
            r, c = start_pos; valid_moves = self.get_valid_moves(r, c)
            for end_pos in valid_moves: possible_ai_moves.append((start_pos, end_pos))
        if not possible_ai_moves: logging.warning("AI has no moves!"); self.ai_thinking = False; return None
        current_board_state = [row[:] for row in self.board]; current_king_pos = self.king_pos
        candidate_moves = [] # Store moves with the best score found so far
        for start_pos, end_pos in possible_ai_moves:
            start_r, start_c = start_pos; end_r, end_c = end_pos; piece_moved = self.board[start_r][start_c]
            self.board[start_r][start_c] = EMPTY; self.board[end_r][end_c] = piece_moved
            score = self.evaluate_board()
            self.board = [row[:] for row in current_board_state]; self.king_pos = current_king_pos
            if score > best_score:
                best_score = score; candidate_moves = [(start_pos, end_pos)] # New best score, reset candidates
            elif score == best_score:
                candidate_moves.append((start_pos, end_pos)) # Add to candidates with same best score
        # Choose randomly among the best moves
        if candidate_moves: best_move = random.choice(candidate_moves)
        logging.info(f"AI chose move: {best_move} from {len(candidate_moves)} candidates with score: {best_score}")
        self.ai_thinking = False; return best_move

    # --- Placeholder Methods ---
    def animate_piece_movement(self, sr, sc, er, ec): pass

    def activate_royal_charge(self):
        """King's special ability to charge through enemy lines."""
        if self.player_turn != 1 or self.king_charge_cooldown > 0:
            return

        king_r, king_c = self.king_pos
        # Royal charge allows king to move 2 squares in any direction, even through knights
        extended_moves = []

        # Add moves that are 2 squares away in any of the 8 directions
        for dr, dc in king_moves:
            nr, nc = king_r + dr * 2, king_c + dc * 2
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                # Check if the destination is empty or has a knight
                if self.board[nr][nc] in [EMPTY, KNIGHT]:
                    # Check if the destination is not under attack
                    if not self.is_square_under_attack(nr, nc):
                        extended_moves.append((nr, nc))

        # If we have valid extended moves, show them
        if extended_moves:
            self.selected_piece_pos = self.king_pos
            self.possible_moves = extended_moves
            self.king_charge_cooldown = 5  # Set cooldown for 5 turns
            logging.info(f"Royal Charge activated. {len(extended_moves)} possible moves.")
        else:
            logging.info("Royal Charge failed - no valid extended moves.")

    def activate_royal_escape(self):
        """King's emergency escape ability - use once per game."""
        if self.player_turn != 1 or not self.king_escape_available:
            return

        king_r, king_c = self.king_pos
        escape_moves = []

        # Find all empty squares not under attack and not adjacent to knights
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == EMPTY and not self.is_square_under_attack(r, c):
                    # Check that it's not adjacent to knights
                    adjacent_to_knight = False
                    for dr, dc in king_moves:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == KNIGHT:
                            adjacent_to_knight = True
                            break

                    if not adjacent_to_knight:
                        escape_moves.append((r, c))

        # Add safe zones as escape options if they're empty
        for r, c in safe_zones:
            if self.board[r][c] == EMPTY:
                escape_moves.append((r, c))

        # If we have valid escape moves, show them
        if escape_moves:
            self.selected_piece_pos = self.king_pos
            self.possible_moves = escape_moves
            self.king_escape_available = False  # One-time use
            logging.info(f"Royal Escape activated. {len(escape_moves)} possible moves.")
        else:
            logging.info("Royal Escape failed - no valid escape moves.")
    def activate_royal_escape(self): logging.info("Royal Escape (Needs Implementation)"); pass
    def update_timers(self, dt): pass

# --- UI Screens ---
def display_homepage(win):
    """Displays the homepage with game mode selection."""
    # --- Unchanged ---
    title_font = pygame.font.Font(None, 74); button_font = pygame.font.Font(None, 50)
    buttons = [ {"text": "Player vs Player", "color": GREEN, "action": "pvp"}, {"text": "Player vs AI", "color": ORANGE, "action": "pva"},
                {"text": "Tutorial", "color": SKY_BLUE, "action": "tutorial"}, {"text": "Settings", "color": YELLOW, "action": "settings"},
                {"text": "Scores", "color": WHITE, "action": "scores"}, {"text": "Exit", "color": RED, "action": "exit"} ]
    button_rects = {}; selected_button = None
    while True:
        win.fill(BLUE); mouse_pos = pygame.mouse.get_pos(); title = title_font.render("Capture the King", True, YELLOW); title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 4 - 20)); win.blit(title, title_rect)
        button_y_start = HEIGHT // 2 - 100; button_height = 55; button_spacing = 15
        for i, button in enumerate(buttons):
            y_pos = button_y_start + i * (button_height + button_spacing); text = button_font.render(button["text"], True, BLACK); text_rect = text.get_rect(center=(WIDTH // 2, y_pos)); button_rect = text_rect.inflate(40, 20)
            is_hovered = button_rect.collidepoint(mouse_pos); button_color = button["color"]
            if is_hovered: button_color = tuple(min(c + 30, 255) for c in button["color"]); selected_button = button["action"]
            else:
                if selected_button == button["action"]: selected_button = None
            pygame.draw.rect(win, button_color, button_rect, border_radius=10); win.blit(text, text_rect); button_rects[button["action"]] = button_rect
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for action, rect in button_rects.items():
                        if rect.collidepoint(mouse_pos):
                            if action in ["pvp", "pva"]: return action
                            elif action == "tutorial": display_tutorial(win)
                            elif action == "settings": display_settings(win)
                            elif action == "scores": display_scores(win)
                            elif action == "exit": pygame.quit(); sys.exit()
        pygame.display.update()
def display_loading_screen(win, image_path, duration=2):
    """Displays a loading screen with fade-in and fade-out animation."""
    try:
        # Load the image
        loading_image = pygame.image.load("Chess.png").convert_alpha()
        loading_image = pygame.transform.scale(loading_image, (650, 650))
    except pygame.error as e:
        logging.error(f"Error loading loading screen image: {e}")
        return

    clock = pygame.time.Clock()
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))  # Black fade surface

    # Fade-in effect
    for alpha in range(0, 256, 5):  # Gradually increase alpha
        fade_surface.set_alpha(255 - alpha)
        win.blit(loading_image, (0, 0))
        win.blit(fade_surface, (0, 0))
        pygame.display.update()
        clock.tick(30)

    # Display the image for a short duration
    pygame.time.delay(int(duration * 1000))

    # Fade-out effect
    for alpha in range(0, 256, 5):  # Gradually decrease alpha
        fade_surface.set_alpha(alpha)
        win.blit(loading_image, (0, 0))
        win.blit(fade_surface, (0, 0))
        pygame.display.update()
        clock.tick(30)
def display_generic_screen(win, title_text, content_lines):
     """Helper function to display simple text screens."""
     # --- Unchanged ---
     win.fill(BLUE); title_font = pygame.font.Font(None, 60); content_font = pygame.font.Font(None, 32); button_font = pygame.font.Font(None, 40)
     title = title_font.render(title_text, True, WHITE); title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 6)); win.blit(title, title_rect)
     line_y_start = HEIGHT // 3
     for i, line in enumerate(content_lines): text = content_font.render(line, True, WHITE); text_rect = text.get_rect(center=(WIDTH // 2, line_y_start + i * 40)); win.blit(text, text_rect)
     back_button_text = button_font.render("Back", True, BLACK); back_button_rect = back_button_text.get_rect(center=(WIDTH // 2, HEIGHT * 5 // 6)); back_button_area = back_button_rect.inflate(40, 20)
     mouse_pos = pygame.mouse.get_pos(); back_color = GREEN
     if back_button_area.collidepoint(mouse_pos): back_color = tuple(min(c + 30, 255) for c in GREEN)
     pygame.draw.rect(win, back_color, back_button_area, border_radius=10); win.blit(back_button_text, back_button_rect); pygame.display.update()
     waiting = True
     while waiting:
         for event in pygame.event.get():
             if event.type == pygame.QUIT: pygame.quit(); sys.exit()
             elif event.type == pygame.MOUSEBUTTONDOWN:
                 if event.button == 1 and back_button_area.collidepoint(pygame.mouse.get_pos()): waiting = False

def display_tutorial(win):
    """Displays the tutorial screen."""
    tutorial_steps = [
        "Welcome to Capture the King!",
        "",
        "Goal: King (P1) vs Knights (P2/AI).",
        "King Moves: 1 square any direction (incl. diagonals).",
        "   - Cannot move into check (attacked square).",
        "   - Can capture Knights by moving onto them.",
        "Knight Moves: L-shape (like chess).",
        "   - Can only move to empty squares.",
        "",
        "King Wins By:",
        "   - Capturing 5 Knights.",
        "   - Reaching any corner (Safe Zone).",
        "Knights Win By:",
        "   - Surrounding the King with 3 Knights.",
        "   - Leaving the King with no valid moves.",
        "   - Surviving for 30 turns (Siege Victory).",
        "",
        "Special Abilities:",
        "   'C' - Royal Charge: King can move 2 squares (5 turn cooldown).",
        "   'E' - Royal Escape: King can teleport once per game.",
        "",
        "Controls: Click to select/move. 'U' to Undo.",
        "   'S' to Save, 'L' to Load."
    ]
    display_generic_screen(win, "Tutorial / How to Play", tutorial_steps)

def display_settings(win):
    """Displays the settings screen (placeholder)."""
    # --- Unchanged ---
    settings_options = [ "Settings (Placeholder)", "", "Board Size: 7x7 (Not changeable yet)", "Knight Count: 6 (Not changeable yet)", "Theme: Classic (Not changeable yet)",
                         "Sound: Off (Removed)", "AI Difficulty: Basic (Not changeable yet)", "", "More options coming soon!" ]
    display_generic_screen(win, "Settings", settings_options)

# --- Score Handling ---
def load_scores(filename="scores.json"):
    # --- Unchanged ---
    default_scores = {"player1_wins": 0, "player2_wins": 0, "player_vs_ai_wins": 0, "ai_wins": 0, "games_played_pvp": 0, "games_played_pva": 0}
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f: scores = json.load(f)
            for key in default_scores:
                if key not in scores: scores[key] = default_scores[key]
            if "games_played" in scores and "games_played_pvp" not in scores: scores["games_played_pvp"] = scores.get("games_played", 0); del scores["games_played"]
            return scores
        except Exception as e: logging.error(f"Error loading scores: {e}. Using defaults."); return default_scores
    return default_scores

def save_scores(scores, filename="scores.json"):
    # --- Unchanged ---
    try:
        scores.pop("games_played", None); scores.pop("player1_wins", None); scores.pop("player2_wins", None) # Clean old keys if desired
        with open(filename, "w") as f: json.dump(scores, f, indent=4); logging.info(f"Scores saved to {filename}")
    except Exception as e: logging.error(f"Error saving scores: {e}")

def update_scores(winner, game_mode):
     # --- Unchanged ---
     scores = load_scores()
     if game_mode == 'pvp': scores["games_played_pvp"] = scores.get("games_played_pvp", 0) + 1
     elif game_mode == 'pva':
          scores["games_played_pva"] = scores.get("games_played_pva", 0) + 1
          if winner == 1: scores["player_vs_ai_wins"] = scores.get("player_vs_ai_wins", 0) + 1
          elif winner == 2: scores["ai_wins"] = scores.get("ai_wins", 0) + 1
     save_scores(scores)

def display_scores(win):
     """Displays game statistics."""
     # --- Unchanged ---
     scores = load_scores(); stats = []; stats.append("Game Statistics"); stats.append(""); stats.append(f"-- Player vs Player --")
     stats.append(f"Games Played: {scores.get('games_played_pvp', 0)}"); stats.append(""); stats.append(f"-- Player vs AI --")
     stats.append(f"Games Played: {scores.get('games_played_pva', 0)}"); stats.append(f" Player Wins: {scores.get('player_vs_ai_wins', 0)}")
     stats.append(f" AI Wins: {scores.get('ai_wins', 0)}")
     pva_games = scores.get('games_played_pva', 0); pva_player_wins = scores.get('player_vs_ai_wins', 0)
     if pva_games > 0: pva_win_rate = (pva_player_wins / pva_games) * 100; stats.append(f" Player Win Rate (vs AI): {pva_win_rate:.1f}%")
     else: stats.append(" Player Win Rate (vs AI): N/A")
     display_generic_screen(win, "Scores", stats)

# --- Main Loop ---
def main():
    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Display the loading screen
    display_loading_screen(win, "loading_screen.jpg")  # Replace with your image path

    while True:  # Outer loop to allow returning to homepage after game ends
        pygame.display.set_caption("Capture the King")
        game_mode = display_homepage(win)
        game = Game(win, game_mode)
        pygame.display.set_caption(f"Capture the King - {'Player vs AI' if game_mode == 'pva' else 'Player vs Player'}")
        game.score_updated = False  # Reset score updated flag for new game

        run_game = True
        while run_game:
            dt = clock.tick(60) / 1000.0

            # AI Turn Logic
            if game.game_mode == 'pva' and game.player_turn == 2 and not game.game_over and not game.ai_thinking:
                ai_move = game.ai_make_move()
                if ai_move:
                    start_pos, end_pos = ai_move
                    game.selected_piece_pos = start_pos  # Select AI piece
                    success = game.attempt_move(end_pos[0], end_pos[1])  # Attempt the move
                    if not success:
                        logging.error(f"AI failed to execute move: {ai_move}")
                else:
                    logging.info("AI returned no move.")
                game.ai_thinking = False  # Ensure flag is cleared

            # Event Handling
            if not game.ai_thinking:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        run_game = False
                        pygame.quit()
                        sys.exit()  # Exit completely on QUIT
                    if not game.game_over:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            if event.button == 1:
                                game.handle_click(event.pos)
                        if event.type == pygame.KEYDOWN:
                            game.handle_keypress(event)
                    elif event.type == pygame.MOUSEBUTTONDOWN:  # Game over, click restarts
                        if event.button == 1:
                            # Instead of just resetting, break inner loop to go to homepage
                            run_game = False
                            # game.reset_game_state() # Reset happens when new game starts

            # Drawing
            game.draw()

            # Update scores if game just ended
            if game.game_over and game.winner != 0:
                if not game.score_updated:
                    update_scores(game.winner, game.game_mode)
                    game.score_updated = True

            # If game ends, clicking will set run_game=False, breaking this loop
            # and returning to the outer loop (homepage)
if __name__ == "__main__":
    main()