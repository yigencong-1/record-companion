"""Parametric spatial study, NOT manufacturing CAD. Requires cadquery 2.7.0, matplotlib."""
from pathlib import Path
import json, math, itertools
import cadquery as cq
P=Path(__file__).resolve().parent
(P/'parts').mkdir(exist_ok=True)
p=json.loads((P/'parameters.json').read_text(encoding='utf-8'))
parts=[]
def box(w,d,h,x=0,y=0,z=0):
    return cq.Workplane('XY').box(w,d,h,centered=(True,True,False)).translate((x,y,z)).val()
def cyl(r,h,x=0,y=0,z=0):
    return cq.Workplane('XY').circle(r).extrude(h).translate((x,y,z)).val()
def ring(ro,ri,h,x=0,y=0,z=0): return cyl(ro,h,x,y,z).cut(cyl(ri,h+2,x,y,z-1))
def y_cyl(r,length,x,y,z):
    return cyl(r,length).rotate((0,0,0),(1,0,0),-90).translate((x,y,z))
def add(name,shape,group,color,explode=(0,0,0),note='study_geometry'):
    parts.append(dict(name=name,shape=shape,group=group,color=color,explode=explode,note=note))
cream=(.87,.83,.73);wood=(.37,.22,.13);frame=(.18,.48,.53);dark=(.13,.15,.18);metal=(.65,.69,.72);orange=(.91,.48,.19)
W,D,H,t=p['case_width'],p['case_depth'],p['case_height'],p['wall'];dy=p['disc_center_y']
sx,sy=p['seat_center_x'],p['seat_center_y'];ro=p['seat_ring_outer_diameter']/2;ri=p['seat_ring_inner_diameter']/2
# Decorative shell: open bottom, front apertures, rear removable service panel.
shell=box(W,D,H-t,z=t).cut(box(W-2*t,D-2*t,H+2,z=t-1))
for x in [-p['speaker_box_center_x'],p['speaker_box_center_x']]: shell=shell.cut(y_cyl(34,10,x,-D/2-2,66))
shell=shell.cut(box(82,10,38,0,-D/2,45)).cut(box(138,10,67,0,D/2,14))
add('01_decorative_shell',shell,'shell',cream,(0,0,90),'front apertures only; grille / gasket / acoustics unresolved')
top=box(W-2*t,D-2*t,4,z=130).cut(cyl(17,8,0,dy,128)).cut(cyl(ro+.5,8,sx,sy,128))
add('02_walnut_visual_top',top,'shell',wood,(0,0,125),'wood appearance only, material not selected')
# Base peripheral load path, central removable hatch.
base=box(W-2*t,D-2*t,3,z=0).cut(box(140,190,5,0,0,-1))
add('03_base_perimeter',base,'frame',cream,(0,0,-25))
add('04_central_bottom_hatch',box(139,189,3,0,0,0),'cover',cream,(0,0,-55),'retention and screw lands not designed')
add('05_rear_service_cover',box(137,3,66,0,D/2-1.5,14),'cover',cream,(0,45,0),'retention not designed')
# Central ladder frame.
for x in [-79,79]: add('rail_left' if x<0 else 'rail_right',box(16,220,12,x,0,3),'frame',frame)
for y in [-102,102]: add('frame_front' if y<0 else 'frame_rear',box(142,16,12,0,y,3),'frame',frame)
for i,(x,y) in enumerate(itertools.product([-79,79],[dy-33,dy+33])):
    s=box(16,16,75,x,y,15).cut(cyl(1.7,80,x,y,13))
    add(f'post_{i+1}',s,'frame',frame)
plate=box(p['bearing_plate_width'],p['bearing_plate_depth'],8,0,dy,p['bearing_plate_z']).cut(cyl(6,12,0,dy,88))
for x,y in itertools.product([-79,79],[dy-33,dy+33]): plate=plate.cut(cyl(1.7,12,x,y,88))
for x,y in itertools.product([-14,14],[dy-14,dy+14]): plate=plate.cut(cyl(1.7,12,x,y,88))
add('06_bearing_support_plate',plate,'frame',frame,(0,0,35))
for i,(x,y) in enumerate(itertools.product([-79,79],[dy-33,dy+33])):
    bolt=cyl(1.5,16,x,y,82).fuse(cyl(3,3,x,y,98))
    add(f'plate_fastener_{i+1}',bolt,'fastener',metal,(0,0,50),'smooth screw envelope, threads / inserts omitted')
bearing=box(36,36,20,0,dy,98).cut(cyl(4.2,24,0,dy,96))
for x,y in itertools.product([-14,14],[dy-14,dy+14]): bearing=bearing.cut(cyl(1.7,24,x,y,96))
add('07_bearing_placeholder',bearing,'drive',metal,(0,0,45),'invented housing; no selected bearing; thrust retention unresolved')
add('08_main_shaft',cyl(4,80,0,dy,64),'drive',metal,(0,0,60),'axial retention not designed')
# Motor supported on removable tray beneath frame.
for sign in [-1,1]:
    bracket=box(16,20,9,sign*79,dy,15).fuse(box(21,20,4,sign*60.5,dy,20)).cut(cyl(1.7,8,sign*54,dy,18))
    add('motor_hanger_L' if sign<0 else 'motor_hanger_R',bracket,'frame',frame,note='upper hanger permits downward tray removal; rail fasteners unresolved')
    bolt=cyl(1.5,8,sign*54,dy,16).fuse(cyl(3,3,sign*54,dy,13))
    add('motor_tray_bolt_L' if sign<0 else 'motor_tray_bolt_R',bolt,'fastener',metal,(0,0,-45),note='smooth bolt envelope; threads omitted')
tray=box(116,74,4,0,dy,16)
for x,y in itertools.product([-42,42],[dy-25,dy+25]): tray=tray.cut(cyl(2,8,x,y,14))
for x in [-54,54]:tray=tray.cut(cyl(1.7,8,x,dy,14))
add('09_motor_tray',tray,'drive',frame,(0,0,-35),'suspended from upper brackets; remove two underside bolts; motor attachment and rail fastening unresolved')
add('10_motor_envelope',box(p['motor_placeholder_width'],p['motor_placeholder_depth'],p['motor_placeholder_height'],0,dy,20),'drive',dark,(0,0,-35),'unselected motor envelope; motor screws omitted')
add('11_motor_output_shaft',cyl(2.5,4,0,dy,60),'drive',metal,(0,0,-35))
coupling=cyl(9,17,0,dy,60).cut(cyl(2.7,4,0,dy,60)).cut(cyl(4.2,15,0,dy,64))
add('12_coupling_placeholder',coupling,'drive',orange,(0,0,-10),'clamping screws and torsion not validated')
platter=cyl(p['disc_diameter']/2,6,0,dy,144)
add('13_platter',platter,'disc',metal,(0,0,150),'shaft attaches at underside face; hub and retainer required')
add('14_decorative_disc',cyl(p['disc_diameter']/2,2,0,dy,150),'disc',dark,(0,0,165),'no physical audio groove, decorative only')
add('15_fixed_light_diffuser',ring(p['disc_diameter']/2-2,p['disc_diameter']/2-6,3,0,dy,134),'lighting',cream,(0,0,130),'fixed to top; LED channel and wiring omitted')
# Two separate sealed-study boxes and simplified driver envelopes.
speaker_air=[]
for sign in [-1,1]:
    x=sign*p['speaker_box_center_x'];y=p['speaker_box_center_y'];bw=p['speaker_box_width'];bd=p['speaker_box_depth'];bh=p['speaker_box_height'];bt=p['speaker_box_wall'];z=12
    interior=box(bw-2*bt,bd-2*bt,bh-2*bt,x,y,z+bt)
    sp=box(bw,bd,bh,x,y,z).cut(interior)
    sp=sp.cut(y_cyl(30,10,x,y-bd/2-2,66))
    label='L' if sign<0 else 'R'
    add('speaker_box_'+label,sp,'acoustic',cream,(sign*65,0,0),'study closed chamber with driver cutout; no removable seam designed')
    flange=y_cyl(34,3,x,y-bd/2-3,66)
    back=y_cyl(29,29,x,y-bd/2,66)
    driver=flange.fuse(back)
    add('speaker_driver_'+label,driver,'acoustic',dark,(sign*65,-25,0),'simplified sealed envelope, not manufacturer CAD')
    speaker_air.append({'side':label,'gross_internal_l':interior.Volume()/1e6,'driver_envelope_in_cavity_l':driver.intersect(interior).Volume()/1e6,'remaining_air_envelope_l':(interior.Volume()-driver.intersect(interior).Volume())/1e6})
# Rear bridge on independent columns, avoids speaker box region (rear edge y=18).
add('rear_bridge_lower_crossmember',box(142,14,12,0,87,3),'frame',frame)
for i,x in enumerate([49,79]):add(f'rear_bridge_post_{i}',box(12,14,103,x,87,15),'frame',frame)
beam_end=sx-(ri-3)+3
bridge=box(beam_end-43,18,6,(43+beam_end)/2,88,118).fuse(ring(ro-4,ri-3,6,sx,sy,118))
bridge=bridge.cut(cyl(ri-3,12,sx,sy,116)).cut(box(52,42,3,sx,sy,121))
add('16_rear_seat_bridge',bridge,'frame',frame,(0,0,30),'cantilever deflection and fastening unresolved')
carrier=ring(ro-2,ri-3,2,sx,sy,124).fuse(ring(ro-2,ri+.2,4,sx,sy,126))
add('17_ring_carrier',carrier,'seat',frame,(0,0,45),'resting contact only; fastening unresolved')
add('18_flush_low_ring',ring(ro,ri,4,sx,sy,130),'seat',cream,(0,0,60))
seat=cyl(ri-.5,3,sx,sy,126).fuse(ring(ri-.5,ri-3,4,sx,sy,129))
add('19_shallow_seat_S1_study',seat,'seat',cream,(0,0,70),'S1 shown as study only; S2 not rejected; finger recess omitted')
add('20_tag_dummy',cyl(p['tag_dummy_diameter']/2,3,sx,sy,129),'seat',orange,(0,0,80),'not birthday geometry; no keyring, hand or RF validation')
add('21_nfc_antenna_envelope',box(50,40,1,sx,sy,122),'electronics',orange,(0,0,20),'envelope only, connector and real antenna shape missing')
# Small electronics placeholders, placed away from motor vertical corridor.
add('22_display_envelope',box(86,12,42,0,-114,43),'electronics',dark,(0,-35,0),'display and FPC unknown; no mount')
add('23_battery_envelope',box(65,42,18,0,62,18),'electronics',orange,(0,30,-10),'not selected pack; no restraint or thermal assessment')
add('24_control_board_envelope',box(65,35,2,0,62,42),'electronics',frame,(0,30,10),'not S31 board outline; connectors and mounting missing')
# Export actual CAD geometry.
for old in (P/'parts').glob('*.step'):
    if old.stem not in {a['name'] for a in parts}: old.unlink()
assembly=cq.Assembly(name='Record_Companion_L3_RESEARCH_ONLY')
for a in parts:
    assembly.add(a['shape'],name=a['name'],color=cq.Color(*a['color']))
    cq.exporters.export(a['shape'],str(P/'parts'/(a['name']+'.step')))
assembly.save(str(P/'record_companion_l3_study.step'))
exploded=cq.Assembly(name='Exploded_RESEARCH_ONLY')
for a in parts: exploded.add(a['shape'].translate(a['explode']),name=a['name'],color=cq.Color(*a['color']))
exploded.save(str(P/'record_companion_l3_exploded.step'))
# Check all positive-volume intersections (contacts are not collisions).
collisions=[]
for a,b in itertools.combinations(parts,2):
    aa,bb=a['shape'].BoundingBox(),b['shape'].BoundingBox()
    if any(min(getattr(aa,axis+'max'),getattr(bb,axis+'max'))-max(getattr(aa,axis+'min'),getattr(bb,axis+'min'))<1e-5 for axis in 'xyz'):continue
    v=a['shape'].intersect(b['shape']).Volume()
    if v>1e-3:collisions.append({'a':a['name'],'b':b['name'],'overlap_mm3':round(v,4)})
report={'status':'RESEARCH ONLY, not a physical validation','part_count':len(parts),'all_shapes_valid':all(a['shape'].isValid() for a in parts),'invalid':[a['name'] for a in parts if not a['shape'].isValid()], 'disconnected_parts':[{'name':a['name'],'solids':len(a['shape'].Solids())} for a in parts if len(a['shape'].Solids())!=1], 'positive_volume_intersections':collisions,'speaker_air':speaker_air,'nominal_disc_to_ring_gap_mm':math.hypot(sx,sy-dy)-p['disc_diameter']/2-ro,'disc_to_fixed_light_axial_gap_mm':144-137,'tests_not_run':['strength','vibration','acoustics','NFC','thermal','fastener design','manufacturing','physical assembly','complete removal swept-volume']}
(P/'geometry_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
meshes=[]
for a in parts:
    vs,fs=a['shape'].tessellate(.7,.2)
    meshes.append({'name':a['name'],'group':a['group'],'color':a['color'],'explode':a['explode'],'vertices':[[round(v.x,3),round(v.y,3),round(v.z,3)] for v in vs],'faces':fs})
(P/'meshes.json').write_text(json.dumps(meshes,separators=(',',':')),encoding='utf-8')
print(json.dumps(report,indent=2))
# Views are rendered from exactly the same tessellated B-rep solids.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def render(filename,groups,title,explosion=False,elev=26,azim=-63):
    fig=plt.figure(figsize=(12,8),facecolor='#f4f0e8');ax=fig.add_subplot(111,projection='3d');ax.set_facecolor('#f4f0e8')
    all_tris=[];all_colors=[]
    for m in meshes:
        if m['group'] not in groups:continue
        off=m['explode'] if explosion else (0,0,0)
        vs=[[v[i]+off[i] for i in range(3)] for v in m['vertices']]
        tris=[[vs[i] for i in f] for f in m['faces']]
        all_tris.extend(tris);all_colors.extend([m['color']]*len(tris))
    poly=Poly3DCollection(all_tris,facecolors=all_colors,linewidths=0,shade=True,lightsource=matplotlib.colors.LightSource(azdeg=315,altdeg=45))
    ax.add_collection3d(poly)
    ax.set_proj_type('ortho')
    ax.set(xlim=(-270,270),ylim=(-195,195),zlim=(-65,340 if explosion else 180));ax.set_box_aspect((540,390,405 if explosion else 245),zoom=1.25);ax.view_init(elev,azim);ax.set_axis_off();fig.suptitle(title+'\nRESEARCH GEOMETRY / NOT MANUFACTURING READY',fontsize=16,color='#26383b',y=.95);plt.subplots_adjust(0,0,1,.91);fig.savefig(P/filename,dpi=150);plt.close(fig)
groups=set(m['group'] for m in meshes)
render('assembled.png',groups,'Record Companion / assembly study')
render('internal.png',groups-{'shell','disc','lighting','cover'},'Internal assembly / top and platter removed',elev=39)
render('exploded.png',groups,'Exploded study / displaced parts for inspection',True,elev=24)
