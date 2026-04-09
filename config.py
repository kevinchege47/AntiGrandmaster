# config.py - Chess Game Configuration
# Customize game behavior here without editing the main code

# ============ ENGINE SETTINGS ============
ENGINE_DEPTH = 8              # Stockfish search depth (6=fast, 8=medium, 10=slow, 12+=very slow)
EVAL_DEPTH = 5                # Position evaluation depth (lower = faster)
ENGINE_DELAY_MS = 1000        # Artificial thinking delay before AI moves (milliseconds)

# ============ DISPLAY SETTINGS ============
DEBUG_MODE = True            # Show FPS counter and move info
SHOW_BEST_MOVE_HINT = True    # Show blue arrow indicating best move (spoilers!)
ENABLE_ANIMATIONS = True      # Animate thinking overlay

# ============ BOARD APPEARANCE ============
BOARD_SIZE = 640              # Size in pixels (640 = 80px per square)
UI_HEIGHT = 140               # Space for top bar
LIGHT_SQUARE_COLOR = (240, 217, 181)    # Tan
DARK_SQUARE_COLOR = (181, 136, 99)      # Brown

# Alternative classic colors:
# LIGHT_SQUARE_COLOR = (240, 240, 240)  # White
# DARK_SQUARE_COLOR = (100, 100, 100)   # Gray

# ============ HIGHLIGHTING COLORS ============
SELECTED_COLOR = (255, 255, 0, 120)     # Yellow for selected piece
LEGAL_MOVE_COLOR = (0, 255, 0, 140)     # Green for legal moves
LAST_MOVE_COLOR = (0, 200, 0, 80)       # Light green for previous move
BEST_MOVE_COLOR = (50, 150, 255)        # Blue for AI's best move hint
CHECK_COLOR = (255, 100, 100, 100)      # Red when in check

# ============ UI THEME ============
BG_COLOR = (20, 20, 20)                 # Dark background
UI_COLOR = (30, 30, 30)                 # Top bar color
TEXT_COLOR = (255, 255, 255)            # Main text
HINT_COLOR = (150, 150, 150)            # Control hints

# ============ DIFFICULTY PRESETS ============
# Use these by setting ENGINE_DEPTH and EVAL_DEPTH together:

# Easy (fast, obviously bad moves):
# ENGINE_DEPTH = 4
# EVAL_DEPTH = 2
# ENGINE_DELAY_MS = 500

# Medium (balanced):
# ENGINE_DEPTH = 8
# EVAL_DEPTH = 5
# ENGINE_DELAY_MS = 1000

# Hard (strong evaluation of bad moves):
# ENGINE_DEPTH = 12
# EVAL_DEPTH = 6
# ENGINE_DELAY_MS = 2000

# Insane (very slow):
# ENGINE_DEPTH = 16
# EVAL_DEPTH = 8
# ENGINE_DELAY_MS = 3000

# ============ GAMEPLAY ============
AUTO_QUEEN_PROMOTION = True   # Auto-promote pawns to queens (vs. prompting)
SHOW_LAST_MOVE = True         # Highlight the last move made
SHOW_CHECK = True             # Highlight king when in check

# ============ TIPS FOR TWEAKING ============
"""
Want to make the AI even WORSE?
  - Lower ENGINE_DEPTH to 4-6 (less analysis of bad moves)
  - Set SHOW_BEST_MOVE_HINT = False (no arrow = harder!)

Want a harder challenge?
  - Increase ENGINE_DEPTH to 12-16 (deeper analysis means fewer stupid moves)
  - Increase EVAL_DEPTH to 6-7
  - Set SHOW_BEST_MOVE_HINT = False

Want faster gameplay?
  - Lower ENGINE_DEPTH to 4
  - Lower EVAL_DEPTH to 2
  - Set ENGINE_DELAY_MS = 300

Want more thinking time animation?
  - Increase ENGINE_DELAY_MS to 2000-3000
"""