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
r={'type':'sampled CAD removal positions, not continuous swept-volume proof','moving':moving,'removed_before_check':removed,'samples':results,'not_modelled':['wiring','actual motor screws','tools and fingers','coupling locking screws','hatch fastening']}
service=[]
cases=[
 ('reader_rear', ['27_reader_rear_service_tray','28_pn7160_core_board'], ['05_rear_service_cover'], (0,1,0)),
 ('battery_bottom', ['23_battery_envelope','26_battery_bottom_service_tray','04_central_bottom_hatch'], [], (0,0,-1)),
 ('antenna_top', ['21_nfc_antenna_envelope','25_nfc_antenna_removable_tray'], ['17_ring_carrier','18_flush_low_ring','19_shallow_seat_S1_study','20_tag_dummy'], (0,0,1)),
]
for label,moved,removed_first,direction in cases:
 samples=[]
 for delta in [2,10,30,60,100]:
  hit=[]
  for name in moved:
   a=files[name].translate(tuple(delta*d for d in direction));aa=a.BoundingBox()
   for k,b in files.items():
    if k in moved+removed_first:continue
    bb=b.BoundingBox()
    if any(min(getattr(aa,x+'max'),getattr(bb,x+'max'))-max(getattr(aa,x+'min'),getattr(bb,x+'min'))<1e-5 for x in 'xyz'):continue
    vol=a.intersect(b).Volume()
    if vol>.001:hit.append([name,k,round(vol,4)])
  samples.append({'offset_mm':delta,'intersections':hit})
 service.append({'route':label,'moving':moved,'removed_before_check':removed_first,'direction':direction,'samples':samples})
r['additional_service_routes']=service
r['limits']='Discrete positions only. Unselected battery, PCB component heights, wire bends, RF clearances and fasteners are not validated.'
(P/'removal_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
