"""Offline single-image chess detector diagnostic; never updates the live game."""
import argparse
import json
import time
from pathlib import Path
import cv2
import numpy as np

BASE = Path(__file__).resolve().parent / 'models' / 'chess-yolov4'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path, help='Original board JPG or PNG')
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    parser.add_argument('--threshold', type=float, default=0.30)
    args = parser.parse_args()
    if not 0 < args.threshold < 1:
        parser.error('--threshold must be between zero and one')
    required = [BASE/'yolov4.custom.cfg', BASE/'yolov4_last.weights', BASE/'data.names']
    for path in required:
        if not path.is_file():
            parser.error(f'Missing model file: {path}. See PIECE-MODEL.md.')
    image = cv2.imdecode(np.frombuffer(args.image.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        parser.error('Input is not a decodable image')
    labels = required[2].read_text().splitlines()
    net = cv2.dnn.readNetFromDarknet(str(required[0]), str(required[1]))
    model = cv2.dnn_DetectionModel(net)
    model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    model.setInputParams(size=(416,416), scale=1/255.0, swapRB=True, crop=False)
    started = time.perf_counter()
    ids, scores, boxes = model.detect(image, confThreshold=args.threshold, nmsThreshold=0.4)
    seconds = time.perf_counter()-started
    annotated = image.copy()
    detections = []
    height, width = image.shape[:2]
    for ident, score, box in zip(np.asarray(ids).reshape(-1), np.asarray(scores).reshape(-1), boxes):
        x,y,w,h = map(int, box)
        label = labels[int(ident)]
        base = [x+w/2, y+h]
        detections.append({'label':label, 'score':float(score), 'box_xywh':[x,y,w,h], 'base_estimate_xy':base})
        p1 = (max(0,x),max(0,y))
        p2 = (min(width-1,x+w),min(height-1,y+h))
        cv2.rectangle(annotated,p1,p2,(0,220,0),2)
        cv2.putText(annotated,f'{label} {score:.2f}',(p1[0],max(18,p1[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,220,0),1,cv2.LINE_AA)
        cv2.circle(annotated,(int(base[0]),int(base[1])),4,(0,165,255),-1)
    args.output.mkdir(parents=True, exist_ok=False)
    ok, encoded = cv2.imencode('.jpg',annotated)
    if not ok:
        raise RuntimeError('Could not encode annotated image')
    (args.output/'annotated.jpg').write_bytes(encoded.tobytes())
    report = {'input':str(args.image.resolve()), 'image_size':[width,height], 'backend':'OpenCV CPU', 'input_size':[416,416], 'threshold':args.threshold, 'inference_seconds':seconds, 'detections':detections, 'limitations':'Unvalidated for this set. Base is box-bottom approximation. No square assignment, FEN or live updates.'}
    (args.output/'detections.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'{len(detections)} detections in {seconds:.2f}s; inspect {args.output}')

if __name__ == '__main__':
    main()
