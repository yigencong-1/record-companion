from pathlib import Path
import json, numpy as np
from PIL import Image,ImageDraw,ImageFont
from matplotlib import font_manager
P=Path(__file__).resolve().parent
meshes=json.loads((P/'meshes.json').read_text())
eye=np.array([550.,-760.,580.]);target=np.array([0.,0.,75.]);f=eye-target;f/=np.linalg.norm(f);r=np.cross([0.,0.,1.],f);r/=np.linalg.norm(r);u=np.cross(f,r);rot=np.array([r,u,f])
for mode in ['internal','assembled','exploded']:
 items=[]
 for m in meshes:
  if mode=='internal' and m['group'] in ['shell','disc','lighting','cover']:continue
  off=np.array(m['explode'] if mode=='exploded' else [0,0,0]);v=(np.array(m['vertices'])+off)@rot.T;items.append((m,v))
 allv=np.concatenate([v for m,v in items]);lo=allv.min(0);hi=allv.max(0);W,H=1500,1060;sc=min(1360/(hi[0]-lo[0]),860/(hi[1]-lo[1]));cen=(lo+hi)/2
 rgb=np.empty((H,W,3),np.uint8);rgb[:]=[244,240,232];depth=np.full((H,W),-np.inf)
 for m,v in items:
  screen=v.copy();screen[:,0]=(v[:,0]-cen[0])*sc+W/2;screen[:,1]=-(v[:,1]-cen[1])*sc+H/2+40
  for face in m['faces']:
   a,b,c=screen[face];xmin=max(0,int(np.floor(min(a[0],b[0],c[0]))));xmax=min(W-1,int(np.ceil(max(a[0],b[0],c[0]))));ymin=max(0,int(np.floor(min(a[1],b[1],c[1]))));ymax=min(H-1,int(np.ceil(max(a[1],b[1],c[1]))))
   den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
   if abs(den)<1e-8 or xmin>xmax or ymin>ymax:continue
   ys,xs=np.mgrid[ymin:ymax+1,xmin:xmax+1];xs=xs+.5;ys=ys+.5
   aa=((b[1]-c[1])*(xs-c[0])+(c[0]-b[0])*(ys-c[1]))/den;bb=((c[1]-a[1])*(xs-c[0])+(a[0]-c[0])*(ys-c[1]))/den;cc=1-aa-bb;zz=aa*a[2]+bb*b[2]+cc*c[2];sub=depth[ymin:ymax+1,xmin:xmax+1];mask=(aa>=-1e-7)&(bb>=-1e-7)&(cc>=-1e-7)&(zz>sub)
   n=np.cross(v[face[1]]-v[face[0]],v[face[2]]-v[face[0]]);n/=max(np.linalg.norm(n),1e-9);shade=.48+.52*abs(np.dot(n,[-.35,.45,.82]));color=np.clip(np.array(m['color'])*shade*255,0,255).astype(np.uint8)
   sub[mask]=zz[mask];rgb[ymin:ymax+1,xmin:xmax+1][mask]=color
 image=Image.fromarray(rgb);d=ImageDraw.Draw(image);font=ImageFont.truetype(font_manager.findfont('DejaVu Sans'),28);small=ImageFont.truetype(font_manager.findfont('DejaVu Sans'),18)
 labels={'internal':'INTERNAL ASSEMBLY / TOP AND PLATTER REMOVED','assembled':'RECORD COMPANION / ASSEMBLY STUDY','exploded':'EXPLODED GEOMETRY / NOT AN ASSEMBLY SEQUENCE'}
 d.text((45,30),labels[mode],font=font,fill='#283c40');d.text((45,72),'Actual CAD geometry | Research only | Dimensions and hardware not approved',font=small,fill='#526365');image.save(P/(mode+'.png'));print(mode)
