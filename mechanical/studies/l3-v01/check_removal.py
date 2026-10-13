from pathlib import Path
import cadquery as cq,json
P=Path(__file__).resolve().parent
files={f.stem:cq.importers.importStep(str(f)).val() for f in (P/'parts').glob('*.step')}
moving=['09_motor_tray','10_motor_envelope','11_motor_output_shaft']
removed=['04_central_bottom_hatch','motor_tray_bolt_L','motor_tray_bolt_R']
results=[]
for delta in [2,10,30,60,100]:
 hit=[]
 for name in moving:
  a=files[name].translate((0,0,-delta));aa=a.BoundingBox()
  for k,b in files.items():
   if k in moving+removed:continue
   bb=b.BoundingBox()
   if any(min(getattr(aa,x+'max'),getattr(bb,x+'max'))-max(getattr(aa,x+'min'),getattr(bb,x+'min'))<1e-5 for x in 'xyz'):continue
   vol=a.intersect(b).Volume()
   if vol>.001:hit.append([name,k,round(vol,4)])
 results.append({'downward_mm':delta,'intersections':hit})
r={'type':'sampled CAD removal positions, not continuous swept-volume proof','moving':moving,'removed_before_check':removed,'samples':results,'not_modelled':['wiring','actual motor screws','tools and fingers','coupling locking screws','hatch fastening']};(P/'removal_report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
