from pathlib import Path
import os,json
ROOT=Path(__file__).resolve().parent
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'settings')

def main():
 import torch
 from ultralytics import YOLO,settings
 settings.update({'sync':False,'wandb':False,'mlflow':False,'comet':False})
 if not torch.cuda.is_available():raise RuntimeError('CUDA GPU unavailable')
 model=YOLO(str(ROOT/'yolo11n.pt'))
 model.train(data=str(ROOT/'yolo-round-02/data.yaml'),device=0,epochs=150,patience=30,imgsz=640,batch=4,workers=0,freeze=0,optimizer='AdamW',lr0=0.001,seed=42,project=str(ROOT/'runs'),name='round-02',exist_ok=False,amp=False,cache=False,plots=True,mosaic=0.5,close_mosaic=10,degrees=8,translate=0.05,scale=0.2,fliplr=0.5,hsv_h=0.01,hsv_s=0.2,hsv_v=0.2)
 run=Path(model.trainer.save_dir)
 best=YOLO(str(run/'weights/best.pt'))
 predictions=best.predict(source=str(ROOT/'yolo-round-02/images/val'),device=0,conf=0.25,save=True,save_txt=True,save_conf=True,project=str(ROOT/'runs'),name='round-02-validation',exist_ok=False)
 (run/'prediction-summary.json').write_text(json.dumps([{'image':Path(r.path).name,'detections_at_conf_025':len(r.boxes)} for r in predictions],indent=2))
 (ROOT/'latest-run.json').write_text(json.dumps({'run':str(run),'weights':str(run/'weights/best.pt'),'validation':'07,08 held out; no independent test set'},indent=2))
 print('Finished. Best weights:',run/'weights/best.pt')
if __name__=='__main__':main()
