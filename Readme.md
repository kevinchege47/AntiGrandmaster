# Actively Bad Chess AI - Refactored Edition

A fun Python chess game where the AI **deliberately plays badly** while showing you the best moves. Features full undo/redo, threading-based AI calculation, and extensive quality improvements.

## Features

✅ **Deliberately Bad AI** - Stockfish recommends the best move (shown as blue arrow), but the AI plays one of the worst legal moves  
✅ **Undo/Redo** - Full move history with branching support  
✅ **Replay** - Step through entire games move by move  
✅ **Threading** - AI thinking doesn't freeze the UI  
✅ **Game Detection** - Automatic checkmate, stalemate, draw detection  
✅ **Visual Feedback** - Last move highlighting, legal move indicators, check highlighting  
✅ **Cross-Platform** - Auto-detects Stockfish and fonts on Linux, macOS, Windows  
✅ **Debug Mode** - Optional FPS and move counter display  

## Installation

### Requirements
- Python 3.8+
- pygame
- python-chess
- Stockfish chess engine

### Setup

1. **Install Python dependencies:**
   ```bash
   pip install pygame python-chess
   ```

2. **Install Stockfish:**
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt install stockfish
   ```
   
   **macOS:**
   ```bash
   brew install stockfish
   ```
   
   **Windows:**
   Download from [stockfishchess.org](https://stockfishchess.org/download/)

3. **Run the game:**
   ```bash
   python really_badchess.py
   ```

## Controls

| Key | Action |
|-----|--------|
| **Mouse Click** | Select piece and move |
| **U** | Undo last move |
| **R** | Redo undone move |
| **N** | Start new game |
| **Q** | Quit |

## Configuration

Edit the `Config` class in the code to customize:

```python
class Config:
    ENGINE_DEPTH = 8          # Stockfish search depth (higher = slower but stronger)
    EVAL_DEPTH = 5            # Position evaluation depth
    ENGINE_DELAY_MS = 1000    # Artificial thinking delay
    SHOW_BEST_MOVE_HINT = True # Show blue arrow for best move
    DEBUG_MODE = False         # Show FPS and move counter
```

## Architecture

### Core Classes

**`Config`** - Centralized configuration with auto-detection
- Finds Stockfish executable across platforms
- Manages all display settings, colors, and fonts
- Configurable engine parameters

**`ChessAI`** - AI engine with threading support
- `get_best_move()` - What Stockfish recommends
- `get_worst_move()` - What the AI actually plays
- `run_ai_move_threaded()` - Non-blocking AI calculation
- Smart move sampling for efficiency

**`GameState`** - Complete game state management
- `make_move()` - Apply moves and update history
- `undo_move()` / `redo_move()` - Full undo/redo support
- `_update_game_status()` - Detects checkmate, stalemate, etc.
- Automatic captured piece tracking

**`ChessRenderer`** - All drawing and UI
- `draw_board()` - Chessboard with piece rendering
- `draw_ui_bar()` - Turn info, move counter, captured pieces
- `draw_thinking_overlay()` - "AI Thinking..." animation
- `draw_game_status()` - Game end messages

**`InputHandler`** - User input processing
- Click detection with validation
- Keyboard shortcuts
- Piece selection and legal move highlighting

**`ChessGame`** - Main game controller
- Orchestrates all systems
- Manages game loop timing
- Resource cleanup

## Improvements Over Original

### Code Quality
- ✅ Proper error handling with try-finally blocks
- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Enum for game states instead of flags
- ✅ Resource cleanup with try-finally patterns

### Performance
- ✅ AI calculation runs in background thread (non-blocking)
- ✅ Move sampling: evaluates only ~30 moves if 100+ legal moves available
- ✅ Caches best move for hint display
- ✅ Early termination in worst-move search

### Features
- ✅ Full undo/redo with move history branching
- ✅ Game status detection (checkmate, stalemate, repetition, 50-move rule)
- ✅ Check highlighting in red
- ✅ Better piece rendering with shadows
- ✅ FPS counter and debug mode

### Robustness
- ✅ Auto-detection of Stockfish across platforms
- ✅ Fallback font system
- ✅ Graceful error messages
- ✅ Thread-safe move queue
- ✅ Board reconstruction for undo functionality

### UI/UX
- ✅ Move counter display
- ✅ Control hints in UI bar
- ✅ Animated thinking indicator
- ✅ Game over overlay with restart prompt
- ✅ Better captured pieces display

## Gameplay Tips

1. **The AI plays badly intentionally** - Use U (undo) to see what the worst move was and learn from AI mistakes

2. **Check the blue arrow** - This shows Stockfish's recommended best move; the AI won't play it!

3. **Build toward endgame** - The AI's poor move choices accumulate into larger advantages

4. **Use Undo/Redo to explore** - Press U to step back through the game and analyze positions

5. **Set DEBUG_MODE=True** for move analysis - See how many moves have been played

## Troubleshooting

**"Stockfish not found" error:**
- Ensure Stockfish is installed and in PATH
- Or specify full path: `ENGINE_PATH = "/path/to/stockfish"`

**Slow AI moves:**
- Reduce `ENGINE_DEPTH` from 8 to 6
- Reduce `EVAL_DEPTH` from 5 to 3
- Increase `ENGINE_DELAY_MS` to see thinking animation

**Font rendering looks bad:**
- Check that `/usr/share/fonts/` exists (Linux)
- Or manually set `FONT_PATH = "/path/to/font.ttf"`

**Game freezes during AI move:**
- This shouldn't happen - AI runs in background thread
- If it does, check that your Python version supports threading properly

## Code Structure

```
chess_game_improved.py
├── Config              # Configuration & auto-detection
├── ChessAI             # Engine interface & AI logic
├── GameState           # Game state & undo/redo
├── ChessRenderer       # UI drawing
├── InputHandler        # User input
├── ChessGame           # Main controller
└── if __name__ == "__main__"
```

## Future Enhancements

Possible additions (not implemented):
- Save/load games to PGN format
- Move time tracking and display
- Difficulty settings (easy/medium/hard)
- Adjustable thinking animation speed
- Opening book for AI first moves
- Engine vs Engine mode
- Network multiplayer

## License

Free to use and modify for educational purposes.

## Credits

- **Stockfish** - Chess engine
- **python-chess** - Chess logic library
- **pygame** - Graphics framework

---

**Want to experiment?** Try tweaking:
- `ENGINE_DEPTH` and `EVAL_DEPTH` for different difficulty levels
- `LIGHT_SQUARE` and `DARK_SQUARE` colors for custom board appearance
- `CONFIG.SHOW_BEST_MOVE_HINT = False` to remove the blue arrow and make it harder!
