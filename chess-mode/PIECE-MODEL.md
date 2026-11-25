# Chess-piece model diagnostic

This is a separate single-image experiment. It does not change app.py, game.py, the live board, or the Pi.

Candidate: https://github.com/rondinellimorais/chess_recognition
The repository includes an MIT license and a twelve-class YOLOv4 configuration. Its README links the pretrained weights separately through Google Drive. The repository license is retained beside the downloaded configuration; separate weight/data provenance should be checked before redistribution.

The local REVISION.txt pins the configuration source. The detector has not been validated on the user's purple chess set. Ordinary OpenCV runs this diagnostic on CPU, even with an RTX 4060 installed.

## Setup on the PC

Run from the repository root with the existing chess virtual environment. The configuration and class labels belong in chess-mode/models/chess-yolov4. Obtain the weights linked by the original README:

https://drive.google.com/open?id=1aY6yIKVfnFlzLUU2jj9bumMCjMJRT9U1

Save them as chess-mode/models/chess-yolov4/yolov4_last.weights. If the public download is available, this command uses gdown (installed separately):

```powershell
chess-mode\.venv\Scripts\python.exe -m gdown 1aY6yIKVfnFlzLUU2jj9bumMCjMJRT9U1 -O chess-mode/models/chess-yolov4/yolov4_last.weights
```

## Run an exact-image test

Save the original board image as board.jpg, then use a new output directory:

```powershell
chess-mode\.venv\Scripts\python.exe -B chess-mode/probe_pieces.py board.jpg --output chess-mode/piece-test-01
```

The script writes annotated.jpg and detections.json. Green boxes show predicted type/side and score; orange dots show estimated box-bottom base points. Check every visible piece manually. These scores are not a guarantee of correctness. There is no board mapping or automatic FEN here: that should only follow an acceptable recognition test.

Do not describe a test on a different camera frame as a test on the original screenshot. The original screenshot was visible in chat but unavailable as a local JPG/PNG when this diagnostic was prepared.

## Preparation result (15 September 2026)

The linked weights were downloaded (256,252,920 bytes). OpenCV successfully loaded the network and ran a synthetic blank-frame smoke test with zero detections. Loading plus that one inference took about 1.79 seconds on this PC. This only checks runtime compatibility; it does not measure chess accuracy or establish sustained video speed. The original board image is still required.

The initial gdown command encountered a certificate verification error on this Windows setup. The successful retry installed truststore through uv using --system-certs, then called truststore.inject_into_ssl() before importing gdown. HTTPS verification remained enabled. The downloaded weights are now already present, so no repeat download is needed.
