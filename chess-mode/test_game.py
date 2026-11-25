import time
import unittest
from unittest.mock import patch

import chess
import numpy as np
from game import Game, Engine, arrow_points, move_squares, rank_moves

class FakeEngine:
    def request(self, board):
        pass
    def result(self, board):
        move = next(iter(board.legal_moves), None)
        return {'status':'Ready', 'uci':move.uci()} if move else {'status':'No move'}

class ChessTests(unittest.TestCase):
    def setUp(self):
        self.corners = np.float32([[100,20],[860,20],[860,520],[100,520]])
        self.image = np.random.default_rng(7).integers(0,255,(540,960,3),np.uint8)

    def test_legal_move_rank(self):
        b=chess.Board()
        scores={s:1 for s in chess.SQUARES}
        scores[chess.E2]=30; scores[chess.E4]=35
        proposed, changed=rank_moves(b,scores)
        self.assertEqual(proposed[0]['uci'],'e2e4')
        self.assertEqual(changed,{chess.E2,chess.E4})

    def test_special_moves(self):
        b=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        self.assertEqual(move_squares(b,chess.Move.from_uci('e1g1')),{chess.E1,chess.G1,chess.H1,chess.F1})
        b=chess.Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        self.assertEqual(move_squares(b,chess.Move.from_uci('e5d6')),{chess.E5,chess.D6,chess.D5})
        b=chess.Board('4k3/P7/8/8/8/8/8/4K3 w - - 0 1')
        scores={s:1 for s in chess.SQUARES}; scores[chess.A7]=30; scores[chess.A8]=30
        proposed,_=rank_moves(b,scores)
        self.assertEqual({p['uci'] for p in proposed},{'a7a8q','a7a8r','a7a8b','a7a8n'})

    def test_no_proposal_for_global_lighting_change(self):
        self.assertEqual(rank_moves(chess.Board(),{s:25 for s in chess.SQUARES})[0],[])

    def test_orientation(self):
        p=arrow_points(chess.Move.from_uci('a8h1'),self.corners,0)
        self.assertLess(p[0][0],p[1][0]); self.assertLess(p[0][1],p[1][1])
        q=arrow_points(chess.Move.from_uci('a8h1'),self.corners,2)
        np.testing.assert_allclose(p[0],q[1],atol=0.01)
        np.testing.assert_allclose(p[1],q[0],atol=0.01)

    def test_record_undo_and_stale_version(self):
        g=Game(FakeEngine()); g.start(self.image,self.corners,'white',0)
        g.stable=True; g.stable_image=g.reference.copy(); g.last_stable=time.monotonic()
        version=g.version
        g.commit('e2e4',version)
        self.assertEqual(g.board.peek().uci(),'e2e4')
        with self.assertRaises(ValueError): g.commit('e7e5',version)
        self.assertIn('e4',g.pgn())
        g.undo(); self.assertEqual(g.board.fen(),chess.Board().fen())
        self.assertIsNone(g.payload(self.corners)['arrow'])

    def test_arrow_requires_clear_stable_board(self):
        g=Game(FakeEngine()); g.start(self.image,self.corners,'white',0)
        self.assertIsNone(g.payload(self.corners)['arrow'])
        with patch('game.time.monotonic',return_value=10): g.observe(self.image,self.corners)
        with patch('game.time.monotonic',return_value=11): g.observe(self.image,self.corners)
        self.assertTrue(g.stable)
        self.assertIsNotNone(g.payload(self.corners)['arrow'])
        g.changed=True; self.assertIsNone(g.payload(self.corners)['arrow'])
        g.observe(self.image,None); self.assertIsNone(g.payload(self.corners)['arrow'])

    def test_started_game_state_serializes_after_stability(self):
        import app
        g=Game(FakeEngine())
        g.start(self.image,self.corners,'white',0)
        with patch('game.time.monotonic',return_value=10):
            g.observe(self.image,self.corners)
        with patch('game.time.monotonic',return_value=11):
            g.observe(self.image,self.corners)
        with patch.object(app,'game',g), patch.object(app,'camera_image',return_value=self.image), patch.object(app.tracker,'update'), patch.object(app.tracker,'corners',self.corners), patch('game.time.monotonic',return_value=12):
            response=app.app.test_client().get('/state')
        self.assertEqual(response.status_code,200)
        self.assertIs(response.json['game']['changed'],False)
        self.assertTrue(response.json['game']['stable'])
        self.assertIsNotNone(response.json['game']['arrow'])

    def test_api(self):
        import app
        client=app.app.test_client()
        self.assertEqual(client.get('/').status_code,200)
        self.assertEqual(client.post('/game/start',json={'side':'white','a8':0}).status_code,400)
        self.assertEqual(client.get('/game/pgn').status_code,400)

if __name__=='__main__':
    unittest.main()
