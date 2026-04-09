import pygame
import chess
import chess.engine
import sys
import os
import random
import threading
from queue import Queue
from pathlib import Path
from typing import Optional, Tuple, List
from enum import Enum


# ====== GAME STATE ENUM ======
class GameStatus(Enum):
    PLAYING = "playing"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    REPETITION = "repetition"
    FIFTY_MOVE = "fifty_move"


# ====== CONFIGURATION ========
class Config:
    """Centralized configuration management"""
    BOARD_SIZE = 640
    UI_HEIGHT = 140
    WIDTH = BOARD_SIZE
    HEIGHT = BOARD_SIZE + UI_HEIGHT
    SQUARE_SIZE = BOARD_SIZE // 8

    # Engine settings
    ENGINE_DEPTH = 8
    EVAL_DEPTH = 5
    ENGINE_DELAY_MS = 1000  # Artificial thinking delay

    # Display settings
    DEBUG_MODE = False
    SHOW_BEST_MOVE_HINT = True
    ENABLE_ANIMATIONS = True

    # Color scheme - improved aesthetics
    LIGHT_SQUARE = pygame.Color(238, 238, 210)  # Softer, warmer cream
    DARK_SQUARE = pygame.Color(118, 150, 86)  # Softer, more professional green
    BG_COLOR = (18, 18, 20)
    UI_COLOR = (28, 28, 32)
    SELECTED_COLOR = (255, 250, 100, 140)  # Softer yellow
    LEGAL_MOVE_COLOR = (100, 200, 100, 160)  # Soft green
    LAST_MOVE_COLOR = (200, 220, 100, 100)  # Soft amber
    BEST_MOVE_COLOR = (100, 180, 255)  # Light blue
    CHECK_COLOR = (255, 120, 120, 140)  # Soft red

    # Fonts
    FONT_LARGE_SIZE = 48
    FONT_MED_SIZE = 28
    FONT_SMALL_SIZE = 60  # For pieces

    # Auto-detect Stockfish
    @staticmethod
    def find_stockfish():
        """Find Stockfish executable in common locations"""
        paths = [
            "/usr/games/stockfish",
            "/usr/bin/stockfish",
            "/opt/homebrew/bin/stockfish",  # macOS
            "C:\\Program Files\\stockfish\\stockfish.exe",  # Windows
            "stockfish",  # Assume in PATH
        ]

        for path in paths:
            if os.path.exists(path) or path == "stockfish":
                try:
                    # Try to run it
                    engine = chess.engine.SimpleEngine.popen_uci(path)
                    engine.quit()
                    return path
                except Exception:
                    continue

        raise FileNotFoundError(
            "Stockfish not found. Install with: apt install stockfish (Linux) "
            "or brew install stockfish (macOS)"
        )

    ENGINE_PATH = find_stockfish()

    # Font path - fallback to system default
    @staticmethod
    def find_font():
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None  # pygame.font.Font will use default

    FONT_PATH = find_font()


# ====== GAME ENGINE ========
class ChessAI:
    """Handles all AI logic with threading support"""

    def __init__(self, engine_path: str):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.move_queue = Queue()
        self.ai_thread: Optional[threading.Thread] = None
        self.is_thinking = False

    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Get objectively best move (Stockfish depth 8)"""
        try:
            result = self.engine.play(board, chess.engine.Limit(depth=Config.ENGINE_DEPTH))
            return result.move
        except Exception as e:
            print(f"Error getting best move: {e}")
            return None

    def evaluate_position(self, board: chess.Board) -> int:
        """Quick evaluation of position (depth 5)"""
        try:
            info = self.engine.analyse(board, chess.engine.Limit(depth=Config.EVAL_DEPTH))
            return info["score"].white().score(mate_score=100000) or 0
        except Exception as e:
            print(f"Error evaluating position: {e}")
            return 0

    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Pick one of the worst legal moves.
        Evaluates positions and chooses move that gives opponent best advantage.
        Uses sampling for efficiency if many legal moves.
        """
        legal_moves = list(board.legal_moves)

        if not legal_moves:
            return None

        if len(legal_moves) == 1:
            return legal_moves[0]

        # Sample subset if too many moves to evaluate
        moves_to_eval = (
            legal_moves
            if len(legal_moves) < 30
            else random.sample(legal_moves, min(30, len(legal_moves)))
        )

        worst_move = moves_to_eval[0]
        worst_score = -float("inf")

        for move in moves_to_eval:
            board.push(move)
            score = self.evaluate_position(board)
            board.pop()

            # Worst for us = best for opponent
            if score > worst_score or (score == worst_score and random.random() < 0.5):
                worst_score = score
                worst_move = move

        return worst_move

    def run_ai_move_threaded(self, board: chess.Board):
        """Calculate AI move in background thread"""
        if self.ai_thread and self.ai_thread.is_alive():
            return

        self.is_thinking = True
        self.ai_thread = threading.Thread(
            target=self._ai_worker,
            args=(board.copy(),),
            daemon=True
        )
        self.ai_thread.start()

    def _ai_worker(self, board_copy: chess.Board):
        """Worker thread for AI calculation"""
        try:
            worst_move = self.get_worst_move(board_copy)
            self.move_queue.put(worst_move)
        except Exception as e:
            print(f"AI worker error: {e}")
            self.move_queue.put(None)
        finally:
            self.is_thinking = False

    def cleanup(self):
        """Safely shutdown engine"""
        try:
            if self.engine:
                self.engine.quit()
        except Exception as e:
            print(f"Error closing engine: {e}")


# ====== GAME STATE ========
class GameState:
    """Manages game state including undo/replay functionality"""

    def __init__(self):
        self.board = chess.Board()
        self.move_history: List[chess.Move] = []
        self.move_index = 0  # Current position in history
        self.last_move: Optional[chess.Move] = None
        self.ai_best_move: Optional[chess.Move] = None

        self.captured_white: List[chess.Piece] = []
        self.captured_black: List[chess.Piece] = []

        self.game_status = GameStatus.PLAYING
        self.status_message = ""

    def make_move(self, move: chess.Move, is_ai: bool = False) -> bool:
        """
        Apply move to board and update history.
        Returns True if successful.
        """
        if move not in self.board.legal_moves:
            return False

        # Handle capture
        if self.board.is_capture(move):
            captured_piece = self.board.piece_at(move.to_square)
            if captured_piece:
                if captured_piece.color == chess.WHITE:
                    self.captured_white.append(captured_piece)
                else:
                    self.captured_black.append(captured_piece)

        # Truncate history if we're not at the end (branching)
        self.move_history = self.move_history[: self.move_index]
        self.move_history.append(move)
        self.move_index = len(self.move_history)

        self.board.push(move)
        self.last_move = move

        self._update_game_status()
        return True

    def undo_move(self) -> bool:
        """Undo last move. Returns True if successful."""
        if self.move_index <= 0:
            return False

        self.move_index -= 1
        move = self.move_history[self.move_index]

        # Reconstruct board from history
        self.board = chess.Board()
        for m in self.move_history[: self.move_index]:
            self.board.push(m)

        # Rebuild captured pieces
        self._rebuild_captures()

        self.last_move = self.move_history[self.move_index - 1] if self.move_index > 0 else None
        self._update_game_status()
        return True

    def redo_move(self) -> bool:
        """Redo last undone move. Returns True if successful."""
        if self.move_index >= len(self.move_history):
            return False

        move = self.move_history[self.move_index]
        self.board.push(move)
        self.move_index += 1
        self.last_move = move

        self._rebuild_captures()
        self._update_game_status()
        return True

    def _rebuild_captures(self):
        """Reconstruct captured pieces from current board state"""
        self.captured_white = []
        self.captured_black = []

        # Standard starting pieces
        starting_white = {
            chess.PAWN: 8,
            chess.KNIGHT: 2,
            chess.BISHOP: 2,
            chess.ROOK: 2,
            chess.QUEEN: 1,
            chess.KING: 1,
        }
        starting_black = starting_white.copy()

        # Count remaining pieces
        remaining_white = {}
        remaining_black = {}

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                if piece.color == chess.WHITE:
                    remaining_white[piece.piece_type] = remaining_white.get(piece.piece_type, 0) + 1
                else:
                    remaining_black[piece.piece_type] = remaining_black.get(piece.piece_type, 0) + 1

        # Calculate captures
        for piece_type in starting_white:
            captured_count = starting_white[piece_type] - remaining_white.get(piece_type, 0)
            for _ in range(captured_count):
                self.captured_black.append(chess.Piece(piece_type, chess.WHITE))

        for piece_type in starting_black:
            captured_count = starting_black[piece_type] - remaining_black.get(piece_type, 0)
            for _ in range(captured_count):
                self.captured_white.append(chess.Piece(piece_type, chess.BLACK))

    def _update_game_status(self):
        """Check game termination conditions"""
        if self.board.is_checkmate():
            self.game_status = GameStatus.CHECKMATE
            self.status_message = (
                "Checkmate! Black Wins!" if self.board.turn == chess.WHITE else "Checkmate! White Wins!"
            )
        elif self.board.is_stalemate():
            self.game_status = GameStatus.STALEMATE
            self.status_message = "Stalemate - Draw"
        elif self.board.is_insufficient_material():
            self.game_status = GameStatus.INSUFFICIENT_MATERIAL
            self.status_message = "Draw - Insufficient Material"
        elif self.board.is_repetition():
            self.game_status = GameStatus.REPETITION
            self.status_message = "Draw - Threefold Repetition"
        elif self.board.is_fifty_moves():
            self.game_status = GameStatus.FIFTY_MOVE
            self.status_message = "Draw - Fifty Move Rule"
        else:
            self.game_status = GameStatus.PLAYING
            self.status_message = ""

    def is_game_over(self) -> bool:
        """Check if game has ended"""
        return self.game_status != GameStatus.PLAYING

    def reset_game(self):
        """Start new game"""
        self.__init__()


# ====== UI RENDERER ========
class ChessRenderer:
    """Handles all drawing and UI rendering"""

    def __init__(self, screen: pygame.Surface, game_state: GameState):
        self.screen = screen
        self.game_state = game_state

        # Initialize fonts
        if Config.FONT_PATH:
            self.font_large = pygame.font.Font(Config.FONT_PATH, Config.FONT_LARGE_SIZE)
            self.font_med = pygame.font.Font(Config.FONT_PATH, Config.FONT_MED_SIZE)
            self.font_small = pygame.font.Font(Config.FONT_PATH, int(Config.SQUARE_SIZE * 0.9))
        else:
            self.font_large = pygame.font.Font(None, Config.FONT_LARGE_SIZE)
            self.font_med = pygame.font.Font(None, Config.FONT_MED_SIZE)
            self.font_small = pygame.font.Font(None, int(Config.SQUARE_SIZE * 0.9))

        self.thinking_animation_frame = 0
        self.animation_clock = pygame.time.Clock()

    @staticmethod
    def square_to_pixel(square: int) -> Tuple[int, int]:
        """Convert chess square (0-63) to pixel coordinates"""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        return (
            file * Config.SQUARE_SIZE,
            (7 - rank) * Config.SQUARE_SIZE + Config.UI_HEIGHT,
        )

    def draw_board(self):
        """Draw chessboard"""
        for row in range(8):
            for col in range(8):
                color = (
                    Config.LIGHT_SQUARE
                    if (row + col) % 2 == 0
                    else Config.DARK_SQUARE
                )
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        col * Config.SQUARE_SIZE,
                        row * Config.SQUARE_SIZE + Config.UI_HEIGHT,
                        Config.SQUARE_SIZE,
                        Config.SQUARE_SIZE,
                    ),
                )

    def draw_check_highlight(self):
        """Highlight king if in check"""
        if self.game_state.board.is_check():
            king_square = self.game_state.board.king(self.game_state.board.turn)
            x, y = self.square_to_pixel(king_square)
            surf = pygame.Surface((Config.SQUARE_SIZE, Config.SQUARE_SIZE), pygame.SRCALPHA)
            surf.fill(Config.CHECK_COLOR)
            self.screen.blit(surf, (x, y))

    def draw_ui_bar(self, selected_square: Optional[int]):
        """Draw top UI bar with move info and controls"""
        # Gradient-style background (darker at edges)
        pygame.draw.rect(self.screen, (25, 25, 28), (0, 0, Config.WIDTH, Config.UI_HEIGHT))
        pygame.draw.line(self.screen, (60, 60, 65), (0, Config.UI_HEIGHT - 1), (Config.WIDTH, Config.UI_HEIGHT - 1), 2)

        # Turn indicator - Bold, prominent
        turn_text = (
            "♔ White to Move" if self.game_state.board.turn == chess.WHITE else "♚ Black to Move"
        )
        turn_render = self.font_med.render(turn_text, True, (255, 255, 255))
        self.screen.blit(turn_render, (20, 12))

        # Move counter - Subtle
        move_count = len(self.game_state.move_history) // 2
        move_text = f"Move {move_count}"
        hint_font = pygame.font.Font(Config.FONT_PATH, 12) if Config.FONT_PATH else pygame.font.Font(None, 12)
        move_render = hint_font.render(move_text, True, (180, 180, 185))
        self.screen.blit(move_render, (20, 48))

        # Control hints - Very subtle, right-aligned
        hints = "U:Undo  R:Redo  N:New  Q:Quit"
        hint_render = hint_font.render(hints, True, (130, 130, 135))
        hint_rect = hint_render.get_rect()
        self.screen.blit(hint_render, (Config.WIDTH - hint_rect.width - 20, 48))

        # Captured pieces display - Left side, organized
        self._draw_captured_pieces()

    def _draw_captured_pieces(self):
        """Draw captured pieces in UI bar with better styling"""
        # Black's captures (white pieces) - top right area
        x_offset = 320
        if self.game_state.captured_black:
            label_font = pygame.font.Font(Config.FONT_PATH, 10) if Config.FONT_PATH else pygame.font.Font(None, 10)
            label = label_font.render("Black captured:", True, (200, 200, 200))
            self.screen.blit(label, (x_offset, 12))
            x_offset = 320
            for piece in self.game_state.captured_black:
                symbol = piece.unicode_symbol()
                text = pygame.font.Font(Config.FONT_PATH, 24) if Config.FONT_PATH else pygame.font.Font(None, 24)
                piece_text = text.render(symbol, True, (140, 140, 140))
                self.screen.blit(piece_text, (x_offset, 28))
                x_offset += 22

        # White's captures (black pieces) - bottom right area
        x_offset = 320
        if self.game_state.captured_white:
            label_font = pygame.font.Font(Config.FONT_PATH, 10) if Config.FONT_PATH else pygame.font.Font(None, 10)
            label = label_font.render("White captured:", True, (200, 200, 200))
            self.screen.blit(label, (x_offset, 72))
            x_offset = 320
            for piece in self.game_state.captured_white:
                symbol = piece.unicode_symbol()
                text = pygame.font.Font(Config.FONT_PATH, 24) if Config.FONT_PATH else pygame.font.Font(None, 24)
                piece_text = text.render(symbol, True, (220, 220, 220))
                self.screen.blit(piece_text, (x_offset, 88))
                x_offset += 22

    def draw_last_move(self):
        """Highlight the last move"""
        if self.game_state.last_move:
            for square in [self.game_state.last_move.from_square, self.game_state.last_move.to_square]:
                x, y = self.square_to_pixel(square)
                surf = pygame.Surface((Config.SQUARE_SIZE, Config.SQUARE_SIZE), pygame.SRCALPHA)
                surf.fill(Config.LAST_MOVE_COLOR)
                self.screen.blit(surf, (x, y))

    def draw_best_move_hint(self):
        """Draw blue arrow showing best move"""
        if Config.SHOW_BEST_MOVE_HINT and self.game_state.ai_best_move:
            start = self.square_to_pixel(self.game_state.ai_best_move.from_square)
            end = self.square_to_pixel(self.game_state.ai_best_move.to_square)

            pygame.draw.line(
                self.screen,
                Config.BEST_MOVE_COLOR,
                (start[0] + Config.SQUARE_SIZE // 2, start[1] + Config.SQUARE_SIZE // 2),
                (end[0] + Config.SQUARE_SIZE // 2, end[1] + Config.SQUARE_SIZE // 2),
                4,
            )

            # Arrowhead
            self._draw_arrow_head(end)

    def _draw_arrow_head(self, pos: Tuple[int, int]):
        """Draw arrowhead at position"""
        size = 12
        points = [
            pos,
            (pos[0] - size, pos[1] - size),
            (pos[0] - size, pos[1] + size),
        ]
        pygame.draw.polygon(self.screen, Config.BEST_MOVE_COLOR, points)

    def draw_highlights(self, selected_square: Optional[int], legal_highlights: List[chess.Move]):
        """Show selected square and legal moves"""
        if selected_square is not None:
            x, y = self.square_to_pixel(selected_square)
            surf = pygame.Surface((Config.SQUARE_SIZE, Config.SQUARE_SIZE), pygame.SRCALPHA)
            surf.fill(Config.SELECTED_COLOR)
            self.screen.blit(surf, (x, y))

        for move in legal_highlights:
            x, y = self.square_to_pixel(move.to_square)
            surf = pygame.Surface((Config.SQUARE_SIZE, Config.SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                Config.LEGAL_MOVE_COLOR,
                (Config.SQUARE_SIZE // 2, Config.SQUARE_SIZE // 2),
                Config.SQUARE_SIZE // 4,
            )
            self.screen.blit(surf, (x, y))

    def draw_pieces(self):
        """Render all pieces using unicode symbols"""
        for square in chess.SQUARES:
            piece = self.game_state.board.piece_at(square)
            if piece:
                symbol = piece.unicode_symbol()
                color = (255, 255, 255) if piece.color == chess.WHITE else (30, 30, 30)

                x, y = self.square_to_pixel(square)
                center = (x + Config.SQUARE_SIZE // 2, y + Config.SQUARE_SIZE // 2)

                # Draw shadow for contrast
                shadow_text = self.font_small.render(symbol, True, (0, 0, 0))
                shadow_rect = shadow_text.get_rect(center=(center[0] + 2, center[1] + 2))
                self.screen.blit(shadow_text, shadow_rect)

                # Draw piece
                text = self.font_small.render(symbol, True, color)
                text_rect = text.get_rect(center=center)
                self.screen.blit(text, text_rect)

    def draw_thinking_overlay(self):
        """Show "AI Thinking..." animation with better styling"""
        overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        box_width, box_height = 360, 140
        box_rect = pygame.Rect(
            Config.WIDTH // 2 - box_width // 2,
            Config.HEIGHT // 2 - box_height // 2,
            box_width,
            box_height,
        )

        # Rounded rectangle background
        pygame.draw.rect(self.screen, (35, 35, 40), box_rect, border_radius=16)
        pygame.draw.rect(self.screen, (120, 180, 255), box_rect, 3, border_radius=16)

        # Animated dots
        dots = "." * ((pygame.time.get_ticks() // 300) % 4)
        text = self.font_large.render(f"AI Thinking{dots}", True, (230, 230, 240))
        text_rect = text.get_rect(center=box_rect.center)
        self.screen.blit(text, text_rect)

    def draw_game_status(self):
        """Show game end status with improved styling"""
        if self.game_state.is_game_over():
            overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))

            box_width, box_height = 480, 200
            box_rect = pygame.Rect(
                Config.WIDTH // 2 - box_width // 2,
                Config.HEIGHT // 2 - box_height // 2,
                box_width,
                box_height,
            )

            pygame.draw.rect(self.screen, (40, 45, 55), box_rect, border_radius=16)
            pygame.draw.rect(self.screen, (150, 200, 255), box_rect, 4, border_radius=16)

            status_text = self.font_large.render(self.game_state.status_message, True, (255, 220, 120))
            status_rect = status_text.get_rect(center=(box_rect.centerx, box_rect.centery - 50))
            self.screen.blit(status_text, status_rect)

            restart_text = self.font_med.render("Press N for New Game", True, (220, 220, 230))
            restart_rect = restart_text.get_rect(center=(box_rect.centerx, box_rect.centery + 40))
            self.screen.blit(restart_text, restart_rect)

    def draw_debug_info(self, fps: float):
        """Show debug info if enabled"""
        if Config.DEBUG_MODE:
            debug_text = f"FPS: {fps:.0f} | Moves: {len(self.game_state.move_history)} | Pos: {self.game_state.move_index}"
            text = self.font_small.render(debug_text, True, (100, 255, 100))
            self.screen.blit(text, (10, 5))

    def render_frame(
            self,
            selected_square: Optional[int],
            legal_highlights: List[chess.Move],
            is_ai_thinking: bool,
            fps: float,
    ):
        """Render complete frame"""
        self.screen.fill(Config.BG_COLOR)
        self.draw_board()
        self.draw_last_move()
        self.draw_best_move_hint()
        self.draw_check_highlight()
        self.draw_highlights(selected_square, legal_highlights)
        self.draw_pieces()
        self.draw_ui_bar(selected_square)

        if is_ai_thinking:
            self.draw_thinking_overlay()

        if self.game_state.is_game_over():
            self.draw_game_status()

        self.draw_debug_info(fps)

        pygame.display.flip()


# ====== INPUT HANDLER ========
class InputHandler:
    """Manages user input"""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.selected_square: Optional[int] = None
        self.legal_highlights: List[chess.Move] = []

    @staticmethod
    def pixel_to_square(x: int, y: int) -> Optional[int]:
        """Convert pixel coordinates to chess square"""
        if y <= Config.UI_HEIGHT or x < 0 or x >= Config.WIDTH:
            return None

        col = x // Config.SQUARE_SIZE
        rank = 7 - ((y - Config.UI_HEIGHT) // Config.SQUARE_SIZE)

        if not (0 <= col < 8 and 0 <= rank < 8):
            return None

        return chess.square(col, rank)

    def handle_click(self, x: int, y: int) -> Optional[chess.Move]:
        """Handle mouse click. Returns move if made, None otherwise."""
        sq = self.pixel_to_square(x, y)

        if sq is None:
            return None

        # First click: select piece
        if self.selected_square is None:
            piece = self.game_state.board.piece_at(sq)
            if piece and piece.color == self.game_state.board.turn:
                self.selected_square = sq
                self.legal_highlights = [
                    m for m in self.game_state.board.legal_moves if m.from_square == sq
                ]
            return None

        # Second click: try to move
        move = chess.Move(self.selected_square, sq)

        if move in self.game_state.board.legal_moves:
            self.selected_square = None
            self.legal_highlights = []
            return move
        else:
            # Try to select new piece instead
            piece = self.game_state.board.piece_at(sq)
            if piece and piece.color == self.game_state.board.turn:
                self.selected_square = sq
                self.legal_highlights = [
                    m for m in self.game_state.board.legal_moves if m.from_square == sq
                ]
            else:
                self.selected_square = None
                self.legal_highlights = []
            return None

    def handle_keyboard(self, key: int) -> str:
        """
        Handle keyboard input.
        Returns action string: 'undo', 'redo', 'new_game', 'quit', or ''
        """
        if key == pygame.K_u:
            self.game_state.undo_move()
            self.selected_square = None
            self.legal_highlights = []
            return "undo"
        elif key == pygame.K_r:
            self.game_state.redo_move()
            self.selected_square = None
            self.legal_highlights = []
            return "redo"
        elif key == pygame.K_n:
            self.game_state.reset_game()
            self.selected_square = None
            self.legal_highlights = []
            return "new_game"
        elif key == pygame.K_q:
            return "quit"

        return ""


# ====== GAME LOOP ========
class ChessGame:
    """Main game controller"""

    def __init__(self):
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))
        pygame.display.set_caption("Actively Bad Chess AI - Refactored")
        self.clock = pygame.time.Clock()

        # Game systems
        self.game_state = GameState()
        self.renderer = ChessRenderer(self.screen, self.game_state)
        self.input_handler = InputHandler(self.game_state)

        try:
            self.ai = ChessAI(Config.ENGINE_PATH)
        except Exception as e:
            print(f"Failed to initialize AI: {e}")
            self.cleanup()
            sys.exit(1)

        self.running = True
        self.ai_thinking_start = 0

    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.game_state.board.turn == chess.WHITE and not self.game_state.is_game_over():
                    x, y = pygame.mouse.get_pos()
                    move = self.input_handler.handle_click(x, y)

                    if move:
                        self.game_state.make_move(move)

            elif event.type == pygame.KEYDOWN:
                action = self.input_handler.handle_keyboard(event.key)
                if action == "quit":
                    self.running = False

    def update_ai(self):
        """Update AI move calculation"""
        black_to_move = (
                self.game_state.board.turn == chess.BLACK
                and not self.game_state.is_game_over()
        )

        # Start AI only once per black turn
        if black_to_move and not self.ai.is_thinking and self.ai.move_queue.empty():
            if Config.DEBUG_MODE:
                print("[AI] Starting move calculation for black")
            self.ai.run_ai_move_threaded(self.game_state.board)
            self.ai_thinking_start = pygame.time.get_ticks()

        # Apply move when ready + delay elapsed (do NOT gate on is_thinking)
        if black_to_move and not self.ai.move_queue.empty():
            elapsed = pygame.time.get_ticks() - self.ai_thinking_start
            if elapsed >= Config.ENGINE_DELAY_MS:
                move = self.ai.move_queue.get()

                if Config.DEBUG_MODE:
                    print(f"[AI] Move ready: {move}")

                if move and move in self.game_state.board.legal_moves:
                    self.game_state.make_move(move)
                    if Config.DEBUG_MODE:
                        print(f"[AI] Black moved: {move}")

                    if not self.game_state.is_game_over():
                        self.game_state.ai_best_move = self.ai.get_best_move(self.game_state.board)
                elif Config.DEBUG_MODE:
                    print(f"[AI] Invalid move: {move}")


    def update(self):
        """Update game state"""
        self.handle_events()
        self.update_ai()

    def render(self):
        """Render frame"""
        self.renderer.render_frame(
            self.input_handler.selected_square,
            self.input_handler.legal_highlights,
            self.ai.is_thinking,
            self.clock.get_fps(),
        )

    def run(self):
        """Main game loop"""
        try:
            while self.running:
                self.update()
                self.render()
                self.clock.tick(60)
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        try:
            self.ai.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            pygame.quit()
            sys.exit()


# ====== ENTRY POINT ========
if __name__ == "__main__":
    game = ChessGame()
    game.run()