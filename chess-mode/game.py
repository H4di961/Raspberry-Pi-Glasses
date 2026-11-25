"""Local chess state, conservative visual move proposals, and Stockfish analysis."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import time

import chess
import chess.engine
import chess.pgn
import cv2
import numpy as np


def orient(corners, a8):
    return np.roll(np.asarray(corners, np.float32), -a8, axis=0)


def board_image(image, corners, a8):
    matrix = cv2.getPerspectiveTransform(orient(corners, a8), np.float32([[0,0],[480,0],[480,480],[0,480]]))
    gray = cv2.cvtColor(cv2.warpPerspective(image, matrix, (480,480)), cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0).astype(np.float32)
    return np.clip((gray-gray.mean()) * (40/max(float(gray.std()), 10)) + 128, 0,255)


def square_changes(before, after):
    diff = np.abs(before-after)
    values = {}
    for square in chess.SQUARES:
        row, col = 7-chess.square_rank(square), chess.square_file(square)
        tile = diff[row*60+6:row*60+54, col*60+6:col*60+54]
        values[square] = float(np.mean(tile))
    return values


def move_squares(board, move):
    next_board = board.copy()
    next_board.push(move)
    return {s for s in chess.SQUARES if board.piece_at(s) != next_board.piece_at(s)}


def rank_moves(board, values):
    floor = float(np.median(list(values.values())))
    changed = {s for s, v in values.items() if v > max(9, floor+6)}
    if len(changed) < 2 or len(changed) > 8:
        return [], changed
    proposals = []
    energy = {s:max(0, v-floor) for s,v in values.items()}
    total = sum(energy.values()) or 1
    for move in board.legal_moves:
        expected = move_squares(board, move)
        common = len(expected & changed)
        agreement = 2*common / (len(expected)+len(changed))
        concentration = sum(energy[s] for s in expected)/total
        score = agreement*0.8 + concentration*0.2
        if common >= 2:
            proposals.append({'uci':move.uci(), 'san':board.san(move), 'match':round(score,3)})
    proposals.sort(key=lambda p:p['match'], reverse=True)
    return proposals[:5], changed


def arrow_points(move, corners, a8):
    matrix = cv2.getPerspectiveTransform(np.float32([[0,0],[8,0],[8,8],[0,8]]), orient(corners,a8))
    points = np.float32([[[chess.square_file(s)+0.5, 7-chess.square_rank(s)+0.5] for s in (move.from_square,move.to_square)]])
    return cv2.perspectiveTransform(points,matrix)[0].tolist()


class Engine:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.fen = None

    def request(self, board):
        if board.fen() == self.fen:
            return
        if self.future:
            self.future.cancel()
        self.fen = board.fen()
        self.future = self.pool.submit(self.analyze, board.copy())

    @staticmethod
    def analyze(board):
        configured = os.environ.get('STOCKFISH_PATH')
        paths = list((Path(__file__).parent/'engine').rglob('*.exe'))
        path = Path(configured) if configured else next((p for p in paths if 'stockfish' in p.name.lower()), None)
        if path is None:
            raise RuntimeError('Stockfish is not installed.')
        with chess.engine.SimpleEngine.popen_uci(str(path), timeout=10) as engine:
            engine.configure({'Threads':2, 'Hash':64})
            info = engine.analyse(board, chess.engine.Limit(time=0.8))
            pv = info.get('pv', [])
            if not pv:
                return {'status':'No legal move.'}
            score = info['score'].white()
            evaluation = ('Mate ' + str(score.mate())) if score.is_mate() else f'{score.score()/100:+.2f}'
            return {'status':'Ready', 'uci':pv[0].uci(), 'san':board.san(pv[0]), 'evaluation':evaluation, 'depth':info.get('depth')}

    def result(self, board):
        if self.fen != board.fen() or not self.future or not self.future.done():
            return {'status':'Stockfish is thinking...'}
        try:
            return self.future.result()
        except Exception as error:
            return {'status':'Engine error: '+str(error)}


class Game:
    def __init__(self, engine=None):
        self.engine = engine or Engine()
        self.board = None
        self.side = chess.WHITE
        self.a8 = 0
        self.version = 0
        self.reference = None
        self.previous = None
        self.stable_image = None
        self.stable_since = None
        self.last_stable = 0
        self.stable = False
        self.changed = False
        self.candidates = []
        self.history = []
        self.status = 'Set up all pieces in their normal starting positions.'

    def invalidate(self):
        self.stable = False
        self.stable_since = None
        self.previous = None
        self.stable_image = None
        self.candidates = []

    def start(self, image, corners, side, a8):
        if side not in ('white','black') or a8 not in range(4):
            raise ValueError('Choose your colour and the corner beside a8.')
        self.board = chess.Board()
        self.side = side == 'white'
        self.a8 = a8
        self.version += 1
        self.history = []
        self.reference = board_image(image,corners,a8)
        self.changed = False
        self.invalidate()
        self.status = 'Starting position recorded. Keep the board clear.'
        if self.board.turn == self.side:
            self.engine.request(self.board)

    def observe(self, image, corners):
        if self.board is None:
            return
        if corners is None:
            self.invalidate()
            self.status = 'Board tracking lost. Recalibrate before continuing.'
            return
        current = board_image(image,corners,self.a8)
        now = time.monotonic()
        if self.previous is None:
            self.previous = current
            self.stable_since = now
            self.stable = False
            return
        motion = square_changes(self.previous,current)
        self.previous = current
        moving = sum(v>7 for v in motion.values()) >= 2 or np.mean(list(motion.values())) > 5
        if moving:
            self.stable_since = now
            self.stable = False
            self.candidates = []
            self.status = 'Movement detected. Waiting for a clear, steady board.'
            return
        if now-(self.stable_since or now) < 0.7:
            self.stable = False
            return
        self.stable = True
        self.stable_image = current
        self.last_stable = now
        values = square_changes(self.reference,current)
        self.candidates, changed = rank_moves(self.board,values)
        self.changed = bool(changed) or bool(np.mean(list(values.values())) > 8)
        if self.changed:
            self.status = 'Review the proposed move, or select the actual legal move below.' if self.candidates else 'Board changed, but the move is unclear. Select the actual legal move or restore the board.'
        elif self.board.is_game_over():
            self.status = 'Game over: '+self.board.result()
        else:
            self.status = ('White' if self.board.turn else 'Black') + ' to move.'

    def commit(self, uci, version):
        if self.board is None or version != self.version:
            raise ValueError('Game changed. Refresh and try again.')
        if not self.stable or self.stable_image is None or time.monotonic()-self.last_stable > 4:
            raise ValueError('Wait for a clear, steady tracked board before recording a move.')
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            raise ValueError('Select a legal move.')
        if move not in self.board.legal_moves:
            raise ValueError('That move is not legal in the recorded position.')
        san = self.board.san(move)
        self.history.append((san,self.reference.copy()))
        self.board.push(move)
        self.reference = self.stable_image.copy()
        self.version += 1
        self.changed = False
        self.invalidate()
        self.status = 'Recorded '+san+'. Waiting for a stable board.'
        if self.board.turn == self.side and not self.board.is_game_over():
            self.engine.request(self.board)

    def undo(self):
        if self.board is None or not self.history:
            raise ValueError('No move to undo.')
        _, self.reference = self.history.pop()
        self.board.pop()
        self.version += 1
        self.changed = True
        self.invalidate()
        self.status = 'Move undone. Restore the physical board to the recorded position.'
        if self.board.turn == self.side:
            self.engine.request(self.board)

    def payload(self, corners):
        if self.board is None:
            return {'active':False, 'status':self.status, 'version':self.version}
        engine = self.engine.result(self.board) if self.board.turn == self.side and not self.board.is_game_over() else {'status':'Waiting for your turn.'}
        arrow = None
        if corners is not None and self.stable and not self.changed and engine.get('uci'):
            move = chess.Move.from_uci(engine['uci'])
            if move in self.board.legal_moves:
                arrow = arrow_points(move,corners,self.a8)
        return {'active':True, 'version':self.version, 'status':self.status, 'fen':self.board.fen(), 'turn':'white' if self.board.turn else 'black', 'side':'white' if self.side else 'black', 'candidates':self.candidates, 'legal':[{'uci':m.uci(),'san':self.board.san(m)} for m in self.board.legal_moves], 'moves':[h[0] for h in self.history], 'engine':engine, 'arrow':arrow, 'stable':self.stable, 'changed':self.changed}

    def pgn(self):
        if self.board is None:
            raise ValueError('Start a game first.')
        return str(chess.pgn.Game.from_board(self.board))
