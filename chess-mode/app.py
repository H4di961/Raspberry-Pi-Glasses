import base64
import os
import threading
import time
import urllib.request

import cv2
import numpy as np
from flask import Flask, jsonify, request, render_template, Response
from waitress import serve
from game import Game

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8_000_000
PI_URL = os.environ.get('PI_CAMERA_URL', 'http://192.168.0.164:8000').rstrip('/')
lock = threading.Lock()

class BoardTracker:
    def __init__(self):
        self.gray = None
        self.points = None
        self.corners = None
        self.status = 'Select the board corners to begin.'

    def lose(self):
        self.corners = None
        self.points = None
        self.status = 'Tracking lost. Select the corners again.'

    def features(self, gray):
        mask = np.zeros_like(gray)
        cv2.fillConvexPoly(mask, self.corners.astype(np.int32), 255)
        return cv2.goodFeaturesToTrack(gray, 180, 0.02, 9, mask=mask)

    def calibrate(self, image, corners):
        corners = np.asarray(corners, dtype=np.float32)
        if corners.shape != (4, 2) or not np.isfinite(corners).all():
            raise ValueError('Select four valid corners.')
        if (corners < 0).any() or (corners > [960, 540]).any():
            raise ValueError('Corners must be inside the image.')
        if not cv2.isContourConvex(corners) or cv2.contourArea(corners) < 8000:
            raise ValueError('Select corners clockwise around the board, not across it.')
        self.corners = corners
        self.gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.points = self.features(self.gray)
        if self.points is None or len(self.points) < 20:
            self.lose()
            raise ValueError('Not enough visible detail. Improve lighting or move closer.')
        self.status = 'Tracking board - move your head slowly.'

    def update(self, image):
        if self.corners is None:
            return
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        nxt, valid, _ = cv2.calcOpticalFlowPyrLK(self.gray, gray, self.points, None, winSize=(31,31), maxLevel=4)
        if nxt is None:
            self.lose(); return
        back, back_valid, _ = cv2.calcOpticalFlowPyrLK(gray, self.gray, nxt, None, winSize=(31,31), maxLevel=4)
        if back is None:
            self.lose(); return
        good = (valid.ravel() == 1) & (back_valid.ravel() == 1) & (np.linalg.norm(self.points-back, axis=2).ravel() < 1.5)
        old = self.points[good].reshape(-1,2)
        new = nxt[good].reshape(-1,2)
        if len(old) < 16:
            self.lose(); return
        matrix, inliers = cv2.findHomography(old, new, cv2.RANSAC, 2.5)
        if matrix is None or not np.isfinite(matrix).all() or inliers.sum() < 14 or inliers.mean() < 0.65:
            self.lose(); return
        old_area = cv2.contourArea(self.corners)
        coverage = cv2.contourArea(cv2.convexHull(old[inliers.ravel() == 1]))
        corners = cv2.perspectiveTransform(self.corners[None], matrix)[0]
        ratio = cv2.contourArea(corners) / max(old_area, 1)
        if (coverage < old_area*0.2 or not np.isfinite(corners).all() or
            not cv2.isContourConvex(corners) or not 0.65 < ratio < 1.5 or
            (corners < 0).any() or (corners > [960,540]).any() or
            np.max(np.linalg.norm(corners-self.corners, axis=1)) > 160):
            self.lose(); return
        self.corners = corners
        self.gray = gray
        self.points = self.features(gray)
        if self.points is None or len(self.points) < 20:
            self.lose(); return
        self.status = 'Tracking board - reset if the outline drifts.'

tracker = BoardTracker()
game = Game()
latest_image = None
latest_time = 0

def camera_image():
    with urllib.request.urlopen(PI_URL + '/frame', timeout=8) as response:
        photo = response.read(8_000_001)
    if len(photo) > 8_000_000:
        raise ValueError('Camera image too large')
    image = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Pi returned an invalid image')
    return cv2.resize(image, (960,540))

@app.get('/state')
def state():
    global latest_image, latest_time
    with lock:
        try:
            image = camera_image()
            tracker.update(image)
            latest_image = image
            latest_time = time.monotonic()
            game.observe(image, tracker.corners)
            ok, jpeg = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise ValueError('Image encoding failed')
            return jsonify(image=base64.b64encode(jpeg).decode(), corners=None if tracker.corners is None else tracker.corners.tolist(), status=tracker.status, game=game.payload(tracker.corners)), 200, {'Cache-Control':'no-store'}
        except Exception:
            app.logger.exception('Camera processing failed')
            tracker.lose()
            game.invalidate()
            return jsonify(error='Cannot process the Pi feed. Check camera connection and try again.'), 503

@app.post('/calibrate')
def calibrate():
    with lock:
        try:
            data = request.get_json()
            photo = base64.b64decode(data['image'], validate=True)
            image = cv2.imdecode(np.frombuffer(photo,np.uint8), cv2.IMREAD_COLOR)
            if image is None or image.shape[:2] != (540,960):
                raise ValueError('Invalid calibration image')
            tracker.calibrate(image, data['corners'])
            game.invalidate()
            return jsonify(ok=True)
        except (ValueError, KeyError, TypeError, cv2.error) as error:
            tracker.lose()
            return jsonify(error=str(error)), 400

@app.get('/')
def home():
    return render_template('chess.html')

@app.post('/game/start')
def start_game():
    with lock:
        try:
            if latest_image is None or tracker.corners is None or time.monotonic()-latest_time > 4:
                raise ValueError('Calibrate the board and wait for the live view first.')
            data = request.get_json(silent=True) or {}
            game.start(latest_image, tracker.corners, data.get('side'), int(data.get('a8', -1)))
            return jsonify(game.payload(tracker.corners))
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400

@app.post('/game/move')
def record_move():
    with lock:
        try:
            if tracker.corners is None:
                raise ValueError('Recalibrate the board first.')
            data = request.get_json(silent=True) or {}
            game.commit(data.get('uci', ''), data.get('version'))
            return jsonify(game.payload(tracker.corners))
        except ValueError as error:
            return jsonify(error=str(error)), 400

@app.post('/game/undo')
def undo_move():
    with lock:
        try:
            game.undo()
            return jsonify(game.payload(tracker.corners))
        except ValueError as error:
            return jsonify(error=str(error)), 400

@app.get('/game/pgn')
def export_game():
    with lock:
        try:
            return Response(game.pgn(), mimetype='application/x-chess-pgn', headers={'Content-Disposition':'attachment; filename=glasses-game.pgn'})
        except ValueError as error:
            return jsonify(error=str(error)), 400

if __name__ == '__main__':
    print('Chess board tracking: http://localhost:8001', flush=True)
    serve(app, host='0.0.0.0', port=8001, threads=4)
