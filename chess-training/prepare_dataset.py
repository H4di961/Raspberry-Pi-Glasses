"""Prepare a reviewable dataset; original captures are never modified."""
from pathlib import Path
import hashlib,json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dataset'
NAMES=['white-pawn','white-rook','white-bishop','white-knight','white-king','white-queen','black-pawn','black-rook','black-bishop','black-king','black-queen','black-knight']
LINEUPS={
 '05': [('black-rook',[148,136,228,257]),('black-knight',[249,132,320,252]),('black-bishop',[330,125,397,245]),('black-king',[399,108,465,246]),('black-queen',[469,98,542,235]),('black-pawn',[547,139,612,240])],
 '06': [('white-rook',[169,108,235,211]),('white-knight',[246,110,306,216]),('white-bishop',[309,106,370,218]),('white-queen',[377,96,435,223]),('white-king',[440,104,507,224]),('white-pawn',[516,138,570,230])]
}
def main():
 manifest_path=OUT/'annotations.json'
 if manifest_path.exists(): raise SystemExit('Dataset already exists; refusing to overwrite reviewed annotations.')
 (OUT/'images').mkdir(parents=True,exist_ok=True)
 images=[]
 for source in sorted(ROOT.glob('*.jpeg.png')):
  ident=source.name.split('.')[0]
  with Image.open(source) as im:
   width,height=im.size
   if im.format!='PNG': raise ValueError('Unexpected image format')
  target=OUT/'images'/f'{ident}.png'
  shutil.copy2(source,target)
  annotations=[{'label':label,'bbox_xyxy':box,'provenance':'Foreground identity confirmed by user; box drawn by assistant'} for label,box in LINEUPS.get(ident,[])]
  for a in annotations:
   x1,y1,x2,y2=a['bbox_xyxy']; assert 0<=x1<x2<=width and 0<=y1<y2<=height
  note='Needs all visible pieces labelled and reviewed.'
  if ident in LINEUPS: note='Foreground lineup labelled using user-confirmed order. Background pieces still need labels. Not complete.'
  if ident=='09': note='Blurry image: excluded from initial training; retain for later difficult-case testing.'
  images.append({'id':ident,'file':f'images/{ident}.png','source':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'width':width,'height':height,'reviewed':False,'excluded':ident=='09','note':note,'annotations':annotations})
 data={'schema_version':1,'classes':NAMES,'box_format':'absolute pixels: x_min,y_min,x_max,y_max','images':images,'status':'Annotation seed only. No training run or dataset split has been made.'}
 manifest_path.write_text(json.dumps(data,indent=2),encoding='utf-8')
 (OUT/'dataset.js').write_text('window.INITIAL_DATASET = '+json.dumps(data)+';',encoding='utf-8')
 print(f'Prepared {len(images)} images and {sum(len(i["annotations"]) for i in images)} foreground annotations.')
if __name__=='__main__': main()
