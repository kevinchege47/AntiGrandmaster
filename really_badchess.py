import pygame
import chess
import chess.engine
import sys
import random

# -------- CONFIGURATION --------
BOARD_SIZE = 640                # Size of the chessboard in pixels (8 × 80 px squares)
UI_HEIGHT = 120                 # Height reserved for top UI bar (turn info + captured pieces)
WIDTH = BOARD_SIZE
HEIGHT = BOARD_SIZE + UI_HEIGHT
SQUARE_SIZE = BOARD_SIZE // 8   # 80 pixels per square
ENGINE_PATH = "/usr/games/stockfish"    # Path to Stockfish executable (Linux default location)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Font used for rendering pieces and text

# -------- INITIALIZATION --------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Actively Bad Chess AI")   # Window title
clock = pygame.time.Clock()

# Different font sizes for different UI elements
font_large = pygame.font.Font(FONT_PATH, 48)
font_med   = pygame.font.Font(FONT_PATH, 28)
font_small = pygame.font.Font(FONT_PATH, int(SQUARE_SIZE * 0.75))  # ≈60 px – good for chess symbols

# Game state variables
board = chess.Board()                           # python-chess board object – core game logic
engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)  # Start Stockfish engine

selected_square = None          # Square currently selected by player (white)
legal_highlights = []           # List of legal target squares from selected piece
ai_thinking_start = 0           # (unused in current code – possibly planned for timing)
game_over = False               # Flag – currently not used
last_move = None                # Last move made (used for highlighting)
ai_best_move = None             # Stockfish's actual best move (shown as blue arrow hint)

captured_white = []             # Pieces captured by black (shown in UI)
captured_black = []             # Pieces captured by white (shown in UI)


# ---------------- UTILITY FUNCTIONS ----------------

def square_to_pixel(square):
    """ Convert chess square (0–63) to pixel coordinates (top-left corner of square) """
    file = chess.square_file(square)          # 0–7 (a–h)
    rank = chess.square_rank(square)          # 0–7 (1–8)
    return (
        file * SQUARE_SIZE,                   # x = file × square size
        (7 - rank) * SQUARE_SIZE + UI_HEIGHT  # y = flipped rank + UI offset
    )


# ---------------- DRAWING FUNCTIONS ----------------

def draw_board():
    """ Draw the 8×8 chessboard with alternating light/dark squares """
    light = pygame.Color(240, 217, 181)
    dark  = pygame.Color(181, 136, 99)

    for row in range(8):
        for col in range(8):
            color = light if (row + col) % 2 == 0 else dark
            pygame.draw.rect(
                screen, color,
                (col * SQUARE_SIZE,
                 row * SQUARE_SIZE + UI_HEIGHT,
                 SQUARE_SIZE, SQUARE_SIZE)
            )


def draw_top_ui():
    """ Draw top bar: turn indicator + captured pieces display """
    pygame.draw.rect(screen, (30, 30, 30), (0, 0, WIDTH, UI_HEIGHT))

    # Turn text
    turn_text = "White to Move" if board.turn == chess.WHITE else "Black to Move"
    turn_render = font_med.render(turn_text, True, (255, 255, 255))
    screen.blit(turn_render, (20, 20))

    # Captured by black (white pieces)
    x_offset = 250
    for piece in captured_white:
        symbol = piece.unicode_symbol()
        text = font_small.render(symbol, True, (255, 255, 255))
        screen.blit(text, (x_offset, 20))
        x_offset += 30

    # Captured by white (black pieces)
    x_offset = 250
    for piece in captured_black:
        symbol = piece.unicode_symbol()
        text = font_small.render(symbol, True, (200, 200, 200))  # Slightly gray for contrast
        screen.blit(text, (x_offset, 60))
        x_offset += 30


def draw_last_move():
    """ Highlight the most recent move with a light green overlay """
    if last_move:
        for sq in [last_move.from_square, last_move.to_square]:
            x, y = square_to_pixel(sq)
            surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            surf.fill((0, 200, 0, 80))          # Semi-transparent green
            screen.blit(surf, (x, y))


def draw_best_move_hint():
    """ Draw a blue arrow showing Stockfish's recommended best move """
    if ai_best_move:
        start = square_to_pixel(ai_best_move.from_square)
        end   = square_to_pixel(ai_best_move.to_square)

        pygame.draw.line(
            screen,
            (50, 150, 255),                     # Light blue
            (start[0] + SQUARE_SIZE // 2, start[1] + SQUARE_SIZE // 2),
            (end[0]   + SQUARE_SIZE // 2, end[1]   + SQUARE_SIZE // 2),
            5
        )


def draw_highlights():
    """ Show selected square (yellow) and legal moves (green dots) """
    # Highlight selected square
    if selected_square is not None:
        x, y = square_to_pixel(selected_square)
        surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        surf.fill((255, 255, 0, 120))           # Semi-transparent yellow
        screen.blit(surf, (x, y))

    # Show legal target squares
    for move in legal_highlights:
        x, y = square_to_pixel(move.to_square)
        surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 255, 0, 140),
                           (SQUARE_SIZE // 2, SQUARE_SIZE // 2),
                           SQUARE_SIZE // 4)
        screen.blit(surf, (x, y))


def draw_pieces():
    """ Render all pieces on the board using Unicode chess symbols """
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            symbol = piece.unicode_symbol()
            color = (255, 255, 255) if piece.color == chess.WHITE else (20, 20, 20)

            x, y = square_to_pixel(square)
            center = (x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)

            text = font_small.render(symbol, True, color)
            text_rect = text.get_rect(center=center)
            screen.blit(text, text_rect)


def draw_thinking_overlay():
    """ Semi-transparent overlay + animated "AI Thinking..." text """
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))                # Dark transparent background
    screen.blit(overlay, (0, 0))

    box_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 80, 400, 160)
    pygame.draw.rect(screen, (40, 40, 40), box_rect, border_radius=12)
    pygame.draw.rect(screen, (100, 100, 255), box_rect, 3, border_radius=12)

    # Animated dots
    dots = "." * ((pygame.time.get_ticks() // 300) % 4)
    text = font_large.render(f"AI Thinking{dots}", True, (255, 255, 255))
    text_rect = text.get_rect(center=box_rect.center)
    screen.blit(text, text_rect)


# ---------------- AI BEHAVIOR (the "actively bad" part) ----------------

def get_best_move():
    """ Ask Stockfish what the objectively best move is (depth 8) """
    result = engine.play(board, chess.engine.Limit(depth=8))
    return result.move


def evaluate_position(temp_board):
    """ Quick evaluation of a position using Stockfish (depth 5) """
    info = engine.analyse(temp_board, chess.engine.Limit(depth=5))
    # Return centipawn score (positive = white advantage), 100000 for mate
    return info["score"].white().score(mate_score=100000) or 0


def get_worst_move():
    """
    Deliberately choose one of the worst legal moves.
    Looks at every legal move, evaluates the position after it,
    and picks the move that gives the **highest score for the opponent**.
    """
    legal_moves = list(board.legal_moves)
    worst_move = None
    worst_score = -float('inf')               # We want to maximize opponent's score

    for move in legal_moves:
        board.push(move)
        score = evaluate_position(board)      # positive = good for white
        board.pop()

        # We want the move that is worst for the side to move
        # → highest score when opponent is to move after our blunder
        if score > worst_score or (score == worst_score and random.random() < 0.5):
            worst_score = score
            worst_move = move

    return worst_move


def ai_make_move():
    """ Black (AI) plays a deliberately terrible move, but shows the best move as hint """
    global last_move, ai_best_move

    # Compute what Stockfish would actually play (for the arrow hint)
    ai_best_move = get_best_move()

    # But actually play something awful
    move = get_worst_move()

    if move:
        # Record captured piece for UI display
        if board.is_capture(move):
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                if captured_piece.color == chess.WHITE:
                    captured_white.append(captured_piece)
                else:
                    captured_black.append(captured_piece)

        board.push(move)
        last_move = move


# ---------------- MAIN GAME LOOP ----------------

running = True

while running:
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if board.turn == chess.WHITE:           # Only white (human) can move
                x, y = pygame.mouse.get_pos()

                if y > UI_HEIGHT:                   # Click inside board area
                    col = x // SQUARE_SIZE
                    rank = 7 - ((y - UI_HEIGHT) // SQUARE_SIZE)
                    sq = chess.square(col, rank)

                    if selected_square is None:
                        # First click: select own piece
                        if board.piece_at(sq) and board.piece_at(sq).color == chess.WHITE:
                            selected_square = sq
                            legal_highlights = [m for m in board.legal_moves if m.from_square == sq]
                    else:
                        # Second click: try to make move
                        move = chess.Move(selected_square, sq)

                        if move in board.legal_moves:
                            # Handle capture for UI
                            if board.is_capture(move):
                                captured_piece = board.piece_at(move.to_square)
                                if captured_piece:
                                    if captured_piece.color == chess.WHITE:
                                        captured_white.append(captured_piece)
                                    else:
                                        captured_black.append(captured_piece)

                            board.push(move)
                            last_move = move
                            selected_square = None
                            legal_highlights = []

    # AI (Black) turn
    if board.turn == chess.BLACK and not board.is_game_over():
        # Show board first
        draw_board()
        draw_top_ui()
        draw_pieces()
        pygame.display.flip()

        # Show thinking animation
        draw_thinking_overlay()
        pygame.display.flip()
        pygame.time.delay(1000)                 # Fake thinking time

        ai_make_move()

    # Normal drawing (most frames)
    screen.fill((0, 0, 0))
    draw_board()
    draw_top_ui()
    draw_last_move()
    draw_best_move_hint()
    draw_highlights()
    draw_pieces()

    pygame.display.flip()
    clock.tick(60)

# Cleanup
pygame.quit()
engine.quit()
sys.exit()