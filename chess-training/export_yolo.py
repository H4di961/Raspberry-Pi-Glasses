from pathlib import Path
import json,shutil,hashlib
import yaml
ROOT=Path(__file__).resolve().parent

def main():
 source=ROOT/'dataset/annotations-reviewed.json'
 data=json.loads(source.read_text(encoding='utf-8-sig'))
 out=ROOT/'yolo-pilot'
 if out.exists(): raise SystemExit('Export exists; refusing to overwrite.')
 records=[]
 for im in data['images']:
  if im['excluded']:continue
  if not im['reviewed']:raise ValueError('Unreviewed image '+im['id'])
  file=ROOT/'dataset'/im['file']
  assert hashlib.sha256(file.read_bytes()).hexdigest()==im['sha256']
  lines=[]
  for a in im['annotations']:
   x1,y1,x2,y2=a['bbox_xyxy'];w,h=im['width'],im['height']
   assert 0<=x1<x2<=w and 0<=y1<y2<=h
   cls=data['classes'].index(a['label'])
   lines.append(f'{cls} {(x1+x2)/2/w:.8f} {(y1+y2)/2/h:.8f} {(x2-x1)/w:.8f} {(y2-y1)/h:.8f}')
  records.append((im,file,lines,'val' if im['id'] in ['07','08'] else 'train'))
 for im,file,lines,split in records:
  (out/'images'/split).mkdir(parents=True,exist_ok=True)
  (out/'labels'/split).mkdir(parents=True,exist_ok=True)
  shutil.copy2(file,out/'images'/split/(im['id']+'.png'))
  (out/'labels'/split/(im['id']+'.txt')).write_text('\n'.join(lines)+'\n')
 (out/'data.yaml').write_text(yaml.safe_dump({'path':out.as_posix(),'train':'images/train','val':'images/val','names':dict(enumerate(data['classes']))},sort_keys=False))
 (out/'manifest.json').write_text(json.dumps({'annotation_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'split':{s:[im['id'] for im,_,_,sp in records if sp==s] for s in ['train','val']},'note':'Pilot only; same room and set. Validation contains two related arrangements and is not an independent benchmark.'},indent=2))
 print('Exported:',[(im['id'],s,len(lines)) for im,_,lines,s in records])
if __name__=='__main__':main()
