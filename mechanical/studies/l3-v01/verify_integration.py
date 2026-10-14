"""Verify generated L3 geometry, B-board envelopes and sampled service routes."""
from pathlib import Path
import json
import cadquery as cq

P = Path(__file__).resolve().parent
geom = json.loads((P/'geometry_report.json').read_text(encoding='utf-8'))
removal = json.loads((P/'removal_report.json').read_text(encoding='utf-8'))
manifest = json.loads((P/'part_manifest.json').read_text(encoding='utf-8'))
parts = {a['name']: a for a in manifest}
assembly = cq.importers.importStep(str(P/'record_companion_l3_study.step')).val()
solids = assembly.Solids()
dimensions = {}
for name, expected in [('21_nfc_antenna_envelope',[44,44,1.6]),('28_pn7160_core_board',[45,32,1.6])]:
    b = parts[name]['bounds_mm']; actual = [b[i+3]-b[i] for i in range(3)]
    assert all(abs(a-e)<1e-6 for a,e in zip(actual,expected)),(name,actual)
    dimensions[name] = actual
routes = {'motor_bottom':removal['samples']}
routes.update({r['route']:r['samples'] for r in removal['additional_service_routes']})
core_bounds=parts['28_pn7160_core_board']['bounds_mm']
reserve=cq.Workplane('XY').box(45,32,6,centered=(True,True,False)).translate((0,103,core_bounds[5])).val()
reserve_hits=[]
for name in parts:
    if name=='28_pn7160_core_board':continue
    shape=cq.importers.importStep(str(P/'parts'/(name+'.step'))).val()
    v=reserve.intersect(shape).Volume()
    if v>.001:reserve_hits.append({'part':name,'intersection_mm3':v})
assert geom['part_count']==len(manifest)==len(solids)==53
assert all(s.isValid() for s in solids)
assert geom['all_shapes_valid'] and not geom['disconnected_parts'] and not geom['positive_volume_intersections']
assert not reserve_hits,reserve_hits
assert all(len(samples)==5 and all(not s['intersections'] for s in samples) for samples in routes.values())
report = {
    'status':'pass', 'revision':'L3 v0.2 integration research',
    'scope':'computed B-rep geometry, STEP roundtrip and discrete service positions only',
    'step_roundtrip_solid_count':len(solids), 'all_step_solids_valid':True,
    'nominal_B_board_dimensions_mm':dimensions,
    'board_source':'project PN7160 B fabrication specification: 45x32 mm 4-layer core; 44x44 mm 2-layer antenna; both nominal 1.6 mm',
    'service_routes_sample_counts':{name:len(samples) for name,samples in routes.items()},
    'positive_volume_intersections':0,
    'core_upper_component_reserve':{'height_mm':6,'intersections':reserve_hits,'basis':'study clearance only; actual component and solder heights pending'},
    'antenna_board_top_to_card_bottom_mm':parts['20_tag_dummy']['bounds_mm'][2]-parts['21_nfc_antenna_envelope']['bounds_mm'][5],
    'L3_inputs_retained':{'case_mm':[400,260,134],'model_top_mm':152,'disc_diameter_mm':220,'shaft_diameter_mm':8},
    'changes':['44x44x1.6 mm antenna plus removable nonmetal study tray and bridge pocket',
               '45x32x1.6 mm core plus rear-service tray and supports',
               'V3 bottom-service concept adapted with independent battery tray; same unselected pack moved 7 mm forward'],
    'unverified':['PCB copper/components/solder-wire geometry and RF clearances','real battery and swelling/thermal requirements',
                  'fastening and insulation','birthday profile/keyring/finger motion','continuous service swept volumes',
                  'acoustics/RF/strength/vibration/thermal/physical assembly'],
}
(P/'integration_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
