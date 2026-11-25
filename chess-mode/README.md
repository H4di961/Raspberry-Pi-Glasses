# Glasses Chess

Run from the repository root:

    chess-mode\.venv\Scripts\python.exe -B chess-mode\app.py

Open http://localhost:8001 on the PC, or http://PC-LAN-IP:8001 on a phone on the same trusted network. The PC stays on. The Pi service stays unchanged. PI_CAMERA_URL defaults to http://192.168.0.164:8000.

## Using it

1. Set the physical board to the normal starting position.
2. Select its four playing-area corners clockwise, starting at the top-left image corner. Hold still while calibrating.
3. Choose your colour and which numbered corner is beside a8 (Black's queenside rook square).
4. Check the starting-position checkbox and click Start game.
5. Move pieces physically. Once the board settles, confirm the correct proposed move or choose it from the legal-move list. Record every move by both players.
6. Stockfish suggests a move on your turn. The yellow arrow is hidden during motion, tracking loss or unrecorded board changes.
7. Undo corrects a recording mistake; restore the physical position too. Download PGN before restarting the server.

Visual change detection is experimental. It proposes legal moves from an initial known position; it does not recognize arbitrary chess pieces. All moves require confirmation. Hand occlusion, head motion, lighting, piece height and optical-flow drift can cause missed or incorrect proposals. Recalibrate if the outline drifts. Verify the recorded digital board. Use one active camera tab.

Stockfish 18 is installed under engine/ from the official project:
https://github.com/official-stockfish/Stockfish/releases/tag/sf_18
The archive retains the engine's license/source materials. No paid API is used. STOCKFISH_PATH can override the executable location. Stockfish uses the CPU; the RTX GPU is not required by this first version.

The game is stored in memory, not persisted across server restarts. The service is intended for a trusted local network, with no Internet port forwarding.

## Tests

    chess-mode\.venv\Scripts\python.exe -B -m unittest discover -s chess-mode -p test_game.py
