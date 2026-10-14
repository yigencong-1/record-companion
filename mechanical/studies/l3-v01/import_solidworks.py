"""Build a local SolidWorks research assembly from generated L3 part STEP files.

Requires Windows, licensed SolidWorks and the project-local solidworks-automation
Skill. Native files and full API evidence are written only to --output-dir.
This produces imported B-rep parts, not native parametric sketch feature trees.
"""
from pathlib import Path
import argparse, json, sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skill-dir', type=Path, default=REPO/'.agents/skills/solidworks-automation')
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    root = args.output_dir.resolve()
    partdir, evidence = root/'parts', root/'evidence'
    partdir.mkdir(parents=True, exist_ok=True); evidence.mkdir(exist_ok=True)
    sys.path.insert(0, str(args.skill_dir/'scripts'))
    import pythoncom
    from win32com.client import VARIANT
    from sw_connect import get_com_member, create_empty_dispatch_variant
    from sw_session import SolidWorksSession
    from sw_assembly import add_component
    from sw_appearance import set_document_appearance
    from sw_review import run_review
    from sw_measure import collect_mass_properties
    manifest = json.loads((HERE/'part_manifest.json').read_text(encoding='utf-8'))
    session = SolidWorksSession(version=2026, wait_seconds=45, visible=True, max_documents=140)
    initial = [str(get_com_member(d, 'GetPathName') or '') for d in list(get_com_member(session.sw, 'GetDocuments') or [])]
    report = {'status':'running', 'native_geometry':'imported STEP B-rep; edit source then regenerate', 'initial_documents':initial, 'parts':[], 'assemblies':[]}
    def persist():
        (evidence/'solidworks-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def close_owned():
        owned=[]
        for d in list(get_com_member(session.sw,'GetDocuments') or []):
            path=str(get_com_member(d,'GetPathName') or '')
            if path and Path(path).resolve().is_relative_to(root):
                if get_com_member(d,'GetSaveFlag') and not session.save(d,path):
                    raise RuntimeError('save dirty owned document '+path)
                owned.append((get_com_member(d,'GetType'),path,get_com_member(d,'GetTitle')))
        for kind,path,title in sorted(owned,key=lambda x:x[0]!=2):
            if session.sw.GetOpenDocumentByName(path) is not None: session.sw.CloseDoc(title)
    def set_fixed(asm,component,fixed):
        asm.ClearSelection2(True)
        if not component.Select4(False,create_empty_dispatch_variant(),False): raise RuntimeError('select component')
        get_com_member(asm,'FixComponent' if fixed else 'UnfixComponent')
        asm.ClearSelection2(True)
        if bool(get_com_member(component,'IsFixed'))!=fixed: raise RuntimeError('fixed state')
    try:
        for item in manifest:
            name=item['name']; path=partdir/(name+'.SLDPRT')
            print('PART '+name,flush=True)
            model=session.open(HERE/'parts'/(name+'.step'),raise_on_error=True)
            if get_com_member(model,'GetType')!=1: raise RuntimeError('STEP did not import as part '+name)
            model.ForceRebuild3(False)
            set_document_appearance(model,item['color'])
            if not session.save(model,path):raise RuntimeError('native save '+name)
            session.close(model)
            model=session.open(path,silent=True)
            bodies=list(get_com_member(model,'GetBodies2',0,False) or [])
            mass=collect_mass_properties(model)
            bbox=[v*1000 for v in get_com_member(model,'GetPartBox',True)]
            expected=item['volume_mm3']; actual=mass.get('volume_mm3')
            if len(bodies)!=1 or actual is None or abs(actual-expected)>max(.01,expected*1e-5):
                raise RuntimeError('part volume/body mismatch '+name)
            # GetPartBox is approximate; it cannot establish tight mechanical clearance.
            err=max(abs(a-b) for a,b in zip(bbox,item['bounds_mm']))
            if err>0.1: raise RuntimeError('part scale/envelope mismatch '+name+' '+str(err))
            report['parts'].append({'name':name,'body_count':len(bodies),'volume_mm3':actual,'expected_volume_mm3':expected,'bounds_mm':bbox,'source_bounds_mm':item['bounds_mm'],'max_bbox_error_mm':err,'save_reopen':True})
            session.close(model); persist()
        mu=get_com_member(session.sw,'GetMathUtility'); mu._FlagAsMethod('CreateTransform')
        identity=(1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.)
        for variant in ['complete','internal']:
            selected=[a for a in manifest if variant=='complete' or a['group'] not in {'shell','disc','lighting','cover'}]
            asm=session.new_assembly(); apath=root/('record_companion_l3_integrated_'+variant+'.SLDASM')
            for i,item in enumerate(selected):
                c=add_component(asm,str(partdir/(item['name']+'.SLDPRT')),sw=session.sw)
                if c is None:raise RuntimeError('insert '+item['name'])
                if get_com_member(c,'IsFixed'):set_fixed(asm,c,False)
                c.Transform2=mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,identity))
                c.Name2='P'+str(i+1).zfill(3)+'_'+item['name']
                set_fixed(asm,c,True)
            asm.ForceRebuild3(False); asm.ViewZoomtofit2()
            if not session.save(asm,apath):raise RuntimeError('assembly save')
            session.close(asm);close_owned()
            asm=session.open(apath,silent=True)
            comps=list(get_com_member(asm,'GetComponents',True) or [])
            if len(comps)!=len(selected):raise RuntimeError('assembly count')
            refs=[]
            for c in comps:
                p=Path(str(get_com_member(c,'GetPathName'))).resolve()
                tr=list(c.Transform2.ArrayData)
                if not p.is_relative_to(partdir) or not p.exists() or not get_com_member(c,'IsFixed') or max(abs(a-b) for a,b in zip(tr,identity))>1e-8:
                    raise RuntimeError('saved reference/transform/fixed mismatch')
                refs.append(p.name)
            if set(refs)!={a['name']+'.SLDPRT' for a in selected}:raise RuntimeError('reference set')
            review,rpath=run_review(asm,evidence,basename='l3_'+variant,views=('isometric','front','top','right'),expected_outputs=[apath])
            report['assemblies'].append({'variant':variant,'component_count':len(comps),'references':refs,'saved_transform_identity':True,'all_fixed':True,'save_reopen':True,'checks':review['checks'],'interference':review['interference'],'evaluation':review.get('evaluation',{})})
            if not review['checks']['previews_not_blank'] or not review['checks']['feature_errors_absent'] or review['interference'].get('interference_count')!=0:
                raise RuntimeError('assembly review '+variant)
            if variant=='complete':
                for ext in ['step','stl']:
                    out=root/('record_companion_l3_sw_export.'+ext)
                    if not session.export(asm,out):raise RuntimeError('SW export '+ext)
                    if out.exists():
                        report[ext+'_export']={'name':out.name,'bytes':out.stat().st_size}
                    elif ext=='stl':
                        members=sorted(root.glob(out.stem+' - *.STL'))
                        if len(members)!=len(manifest):raise RuntimeError('incomplete split STL export')
                        report['stl_export']={'layout':'one STL per component','file_count':len(members),'files':[{'name':f.name,'bytes':f.stat().st_size} for f in members]}
                    else:raise RuntimeError('export API returned without expected file '+ext)
            if get_com_member(asm,'GetSaveFlag') and not session.save(asm,apath):raise RuntimeError('final save')
            session.close(asm);close_owned();persist()
        report['status']='pass'; report['limits']=['fixed research assembly, no kinematic mates','STEP-imported solids, not editable SW sketches','unselected placeholders remain','no physical RF/acoustic/thermal/strength validation']
    except Exception as exc:
        report['status']='failed';report['error']=str(exc);persist();raise
    finally:
        close_owned()
        remaining=[str(get_com_member(d,'GetPathName') or '') for d in list(get_com_member(session.sw,'GetDocuments') or [])]
        report['remaining_documents']=remaining
        report['owned_documents_saved_closed']=not any(p and Path(p).is_relative_to(root) for p in remaining)
        # Only an instance started for this run may be closed automatically.
        report['quit_owned_instance']=session.quit_owned_instance()
        persist()
    print(json.dumps({'status':report['status'],'parts':len(report['parts']),'assemblies':len(report['assemblies'])}),flush=True)

if __name__=='__main__':main()
