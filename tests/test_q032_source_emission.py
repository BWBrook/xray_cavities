from pathlib import Path
import json
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/science'))
import build_q032_source_emission as emission


def grid(n=8,limit=4.):
    edges=np.linspace(-limit,limit,n+1);centres=(edges[:-1]+edges[1:])/2;d=np.diff(edges)
    return emission.Grid(centres,centres,centres,d,d,d,edges,edges,edges,'synthetic_exact_edges')


def state(shape):
    return {'rho':np.ones(shape),'prs':np.ones(shape), 'tr1':np.zeros(shape),
            'vx1':np.zeros(shape),'vx2':np.zeros(shape),'vx3':np.zeros(shape)}


def fake_emissivity(rho,pressure):
    values={key:rho**2 for convention in emission.CONVENTIONS for key in (convention,convention+'_before')}
    return values,np.ones_like(rho),{'any':np.zeros(rho.shape,dtype=bool),'raw_nonfinite':np.zeros(rho.shape,dtype=bool)}


def test_partition_uses_float64_strict_tracer_full_speed_and_slow_cocoon():
    tracer=np.array([.002,.001,0.,0.,0.],dtype=np.float64)
    scale=1e5/emission.budget.UNIT_VELOCITY_CMS
    vx=np.array([0,100,60,0,0])*scale
    vy=np.array([0,0,80,0,0])*scale
    vz=np.array([0,0,0,100,99])*scale
    masks=emission.partition_masks(tracer,(vx,vy,vz),100)
    assert masks['C'].tolist()==[True,False,False,False,False]
    assert masks['A'].tolist()==[False,True,True,True,False]
    assert np.all(sum(mask.astype(int) for mask in masks.values())==1)
    f32=emission.partition_masks(np.array([.001],dtype=np.float32),(np.zeros(1),)*3,100)
    assert f32['C'][0] # float32's stored 0.001 is above the exact float64 threshold.


def test_signed_ratio_is_unbounded_and_handles_absent_or_cancelled_deficit():
    assert emission.signed_ratio(2.,1.,5.)['ratio']==2.
    assert emission.signed_ratio(-2.,1.,5.)['ratio']==-2.
    assert emission.signed_ratio(1.,0.,5.)['ratio'] is None
    assert emission.signed_ratio(1.,1e-14,5.)['near_zero_denominator']


def test_asymmetric_holey_revolution_preserves_radial_intervals_and_exact_moments():
    u=np.arange(-4.,5.)
    mask=np.array([[True,False,True,False,False,True,False,False]])
    radius=np.array([[.5,1.5,2.5,3.5]])
    assert emission.revolution_membership(mask[0],u,radius,'W+').tolist()==[[False,True,False,False]]
    assert emission.revolution_membership(mask[0],u,radius,'W-').tolist()==[[False,True,False,True]]
    moments=emission.native.exact_abs_u_moments(mask,u,np.array([-1.,1.]))
    assert moments['positive_u_revolution_kpc3']==pytest.approx(6*np.pi)
    assert moments['negative_u_revolution_kpc3']==pytest.approx(20*np.pi)
    assert moments['symmetrized_revolution_kpc3']==pytest.approx(13*np.pi)


def test_native_revolution_volume_converges_to_holey_analytic_solid():
    errors=[]
    edges=np.arange(-4.,5.)
    mask=np.array([False,False,False,False,False,True,False,True])
    exact=np.pi*((2**2-1**2)+(4**2-3**2))*2
    for n in (32,160):
        coords=np.linspace(-4,4,n,endpoint=False)+4/n
        radii=np.hypot(coords[:,None],coords[None,:])
        cells=emission.revolution_membership(mask,edges,radii,'W+')
        measured=cells.sum()*(8/n)**2*2
        errors.append(abs(measured-exact))
    assert errors[1]<errors[0]
    assert errors[1]/exact<.005


@pytest.mark.parametrize('angle',[0,45,90])
def test_exact_projection_area_and_component_closure(angle):
    g=grid()
    horizontal=g.x if angle==0 else emission.native.renderer.projected_axis(g.x,g.y,view_angle_deg=angle,projected_u_bins=12)[0]
    v=emission.make_view(g,angle,horizontal,np.ones((8,len(horizontal))),{})
    values=np.arange(64.).reshape(8,8)
    projected=emission.project_scalar(v,values,g)
    assert np.sum(projected*np.diff(v.u_edges))==pytest.approx(np.sum(values*v.covered_area_xy))
    emission.closure('partition',emission.project_scalar(v,values*(values<32),g)+emission.project_scalar(v,values*(values>=32),g),projected)


def test_truncated_sky_grid_reports_coverage_loss_without_renormalizing():
    g=grid();v=emission.make_view(g,90,np.linspace(-2,2,5),np.ones((8,5)),{})
    assert v.geometry_report['projection_coverage_hold']
    assert v.covered_area_xy.sum()<np.outer(g.dy,g.dx).sum()
    assert np.sum(emission.project_scalar(v,np.ones((8,8)),g)*np.diff(v.u_edges))==pytest.approx(v.covered_area_xy.sum())


def test_one_pass_current_masks_apply_to_initial_and_native_filling_uses_own_denominator():
    g=grid();shape=(8,8,8);now=state(shape);zero=state(shape)
    now['tr1'][:,:,:4]=.5
    now['rho'][:,:,4:]=2
    now['vx1'][:,:,4:]=200e5/emission.budget.UNIT_VELOCITY_CMS
    zero['rho'][:,:,4:]=3
    observer={'mask':np.ones((8,8),dtype=bool),'background':np.ones((8,8)),'condition_number':1.,'support_threshold':.05}
    v=emission.make_view(g,0,g.x,np.ones((8,8)),{method:observer for method in emission.METHODS})
    rows,diag=emission.integrate_native(now,zero,g,{0:v},fake_emissivity)
    # Slow cocoon stays in C; current moving-ambient mask selects the same initial cells.
    assert np.allclose(v.maps['brightness_initial_retained_linear_A_v100'][:,4:],9*8*emission.BRIGHTNESS_FACTOR)
    assert np.all(v.maps['brightness_initial_retained_linear_A_v100'][:,:4]==0)
    assert np.all(v.maps['path_C_kpc'][:,:4]==8)
    assert np.all(v.maps['path_A_v300_kpc']==0)
    positive=next(row for row in rows if row['solid']=='W+' and row['hemisphere']=='bipolar_total')
    assert positive['volume_kpc3_share']==pytest.approx(.5)
    assert positive['mass_g_share']==pytest.approx(1/3)
    assert positive['pressure_integral_erg_share']==pytest.approx(.5)
    assert positive['volume_kpc3_numerator']<=positive['volume_kpc3_denominator']
    assert diag['disturbed_ambient_cell_count_by_speed'][4]==256
    assert diag['native_component_boundary_cell_counts']['C']=={
        'x_min':64,'x_max':0,'y_min':32,'y_max':32,'z_min':32,'z_max':32}
    assert diag['native_component_boundary_cell_counts']['A_v100']['x_max']==64
    # For a brighter current ambient, signed D_A is negative rather than clipped.
    now['rho'][:,:,4:]=4
    v2=emission.make_view(g,0,g.x,np.ones((8,8)),{method:observer for method in emission.METHODS})
    emission.integrate_native(now,zero,g,{0:v2},fake_emissivity)
    assert np.all((v2.maps['brightness_initial_retained_linear_A_v100']-v2.maps['brightness_current_retained_linear_A_v100'])[:,4:]<0)


def test_compact_identity_rejects_wrong_table_or_mask_hash(tmp_path):
    path=tmp_path/'table.txt';path.write_text('original')
    digest=emission.budget._sha256(path)
    assert emission.checked_compact({'path':str(path),'sha256':digest})['sha256']==digest
    path.write_text('different')
    with pytest.raises(ValueError,match='identity mismatch'):
        emission.checked_compact({'path':str(path),'sha256':digest})


def test_packed_mask_identity_dimensions_fail_closed():
    with pytest.raises(ValueError,match='invalid packed'):
        emission.unpack_mask({'mask':np.array([True])},'mask',(2,2))


def test_fixed_background_detection_differs_from_refitting_and_reproduces_original():
    h=np.linspace(-200,200,161);z=np.linspace(-200,200,161);xx,zz=np.meshgrid(h,z)
    image=np.ones_like(xx)*100
    cavity=(xx/22)**2+((zz-60)/28)**2<1
    image[cavity]*=.65
    original=emission.original_observers(image,h,z)
    for method,record in original.items():
        assert np.array_equal(emission.detect_fixed(image,h,z,method,record),record['mask'])
    assert original[emission.METHODS[1]]['mask'].sum()>0
    replacement=image*2
    fixed=emission.detect_fixed(replacement,h,z,emission.METHODS[1],original[emission.METHODS[1]])
    refit=emission.original_observers(replacement,h,z)[emission.METHODS[1]]['mask']
    assert not np.array_equal(fixed,refit)
    assert not fixed.any()
    assert np.array_equal(refit,original[emission.METHODS[1]]['mask'])


@pytest.mark.parametrize('angle', [0, 45, 90])
def test_correction_weights_match_explicit_flagged_maps_with_signed_cancellation(angle):
    g=grid();horizontal=g.x if angle==0 else emission.native.renderer.projected_axis(
        g.x,g.y,view_angle_deg=angle,projected_u_bins=12)[0]
    mask=np.zeros((8,len(horizontal)),dtype=bool);mask[2:6,1:-1]=True
    view=emission.make_view(g,angle,horizontal,np.ones_like(mask,dtype=float),{'test':{'mask':mask}})
    index=np.arange(64).reshape(8,8)
    regions={'C':index<16,**{f'{r}_v{cut}':(index>=16)&((index%2==0) if r=='A' else (index%2!=0))
                          for cut in emission.CUTS for r in ('A','E')}}
    retained=np.where(index%3==0,-2.,1.)
    values={'retained_linear':retained,'clamp_each_coordinate':np.abs(retained)*2}
    fields={'current':values,'initial':{k:3*v for k,v in values.items()}}
    domains={state:{'out_of_table':index%4!=0,'retained_negative':retained<0} for state in fields}
    expected={}
    for iz in range(8):
        emission.accumulate_corrections(view,iz,g,regions,fields,domains)
        for state in fields:
            for convention in emission.CONVENTIONS:
                for region in (*emission.REGIONS,'whole'):
                    selected=np.ones((8,8),bool) if region=='whole' else regions[region]
                    for domain,flag in domains[state].items():
                        flagged=fields[state][convention]*selected*flag*emission.BRIGHTNESS_FACTOR
                        signed=emission.project_scalar(view,flagged,g)
                        absolute=emission.project_scalar(view,np.abs(flagged),g)
                        for side in emission.SIDES:
                            if side=='negative_z' and g.z[iz]>=0 or side=='positive_z' and g.z[iz]<=0:continue
                            key=('test',side,state,convention,region,domain)
                            result=np.array([np.sum(q*mask[iz]*np.diff(view.u_edges))*g.dz[iz] for q in (signed,absolute)])
                            expected[key]=expected.get(key,np.zeros(2))+result
    for key,value in expected.items():
        np.testing.assert_allclose(view.correction_contributions[key],value,rtol=2e-14,atol=2e-14*value[1])
    key=('test','bipolar_total','current','retained_linear','whole','out_of_table')
    signed,absolute=view.correction_contributions[key]
    assert absolute>abs(signed)
    reference={'view_deg':angle,'method':'test','hemisphere':'bipolar_total','correction':'retained_linear',
               'velocity_cut_km_s':100,'observed_deficit_integral':2.,'denominator_reference_scale':5.,
               'cocoon_deficit_integral':3.,'moving_ambient_deficit_integral':-1.,'external_deficit_integral':4.}
    rows=emission.correction_rows({angle:view},[reference])
    selected=[r for r in rows if r['region']=='whole' and r['correction_domain']=='out_of_table']
    assert sum(r['signed_deficit_contribution'] for r in selected)==pytest.approx(2*signed,abs=2e-14*absolute)
    assert all(r['component_signed_deficit_integral']==6 for r in selected)
    assert next(r for r in selected if r['state']=='current')['signed_deficit_contribution']==pytest.approx(-signed)


@pytest.mark.parametrize('fault', ['native_path','timestep','time','projection','axis','xraise_source','apec_table','gaunt_lut'])
def test_retained_map_metadata_rejects_wrong_native_or_projection_identity(tmp_path,fault):
    g=grid();source=tmp_path/'native.h5';source.touch()
    image=tmp_path/'image.txt';horizontal=tmp_path/'horizontal.txt';vertical=tmp_path/'vertical.txt';metadata=tmp_path/'metadata.json'
    np.savetxt(image,np.ones((8,8)));np.savetxt(horizontal,g.x);np.savetxt(vertical,g.z)
    record={'input_h5':str(source),'timestep':'Timestep_20','grid_shape_nz_ny_nx':[8,8,8],
            'time_code':20.,'frequency_hz':1e17,'redshift':.1,
            'projection':{'view_angle_deg':0,'sky_horizontal_bins':8,'projected_accumulation':emission.native.renderer.resolve_projection_method(0,'auto')}}
    inputs={role:{'path':str(tmp_path/role)} for role in ('xraise_py','apec_table','gaunt_lut')}
    record.update({key:inputs[role]['path'] for key,role in [('xraise_source','xraise_py'),('apec_table','apec_table'),('gaunt_lut','gaunt_lut')]})
    if fault=='native_path':record['input_h5']=str(tmp_path/'other.h5')
    if fault=='timestep':record['timestep']='Timestep_40'
    if fault=='time':record['time_code']=40.
    if fault=='projection':record['projection']['view_angle_deg']=90
    if fault=='axis':np.savetxt(vertical,g.z+.1)
    if fault in ('xraise_source','apec_table','gaunt_lut'):record[fault]=str(tmp_path/'different-source')
    metadata.write_text(json.dumps(record))
    contract={'frequency_hz':1e17,'redshift':.1,'inputs':inputs,'views':{'0':{role:{'path':str(path)} for role,path in
              [('image',image),('horizontal',horizontal),('vertical',vertical),('metadata',metadata)]}}}
    receipt={'inputs':{'current_h5':{'resolved_path':str(source)}},'current':{'timestep':'Timestep_20','time_code':20.}}
    with pytest.raises(ValueError,match='differs|mismatch'):
        emission.load_views(contract,receipt,g,(8,8,8))


@pytest.mark.parametrize('angle',[0,45])
def test_complete_arithmetic_retains_signed_deficits_and_cancellation_closures(monkeypatch,angle):
    g=grid();shape=(8,8,8);now=state(shape);zero=state(shape)
    now['tr1'][:,:,:4]=.5;now['rho'][:,:,4:]=2.;zero['rho'][:]=3.
    now['vx1'][:,:,4:]=200e5/emission.budget.UNIT_VELOCITY_CMS
    horizontal=g.x if angle==0 else emission.native.renderer.projected_axis(
        g.x,g.y,view_angle_deg=angle,projected_u_bins=12)[0]
    projected_shape=(8,len(horizontal))
    observer={'mask':np.ones(projected_shape,dtype=bool),'background':np.full(projected_shape,10*emission.BRIGHTNESS_FACTOR),
              'condition_number':1.,'support_threshold':.05}
    observers={method:observer for method in emission.METHODS}
    view=emission.make_view(g,angle,horizontal,np.zeros(projected_shape),observers)
    monkeypatch.setattr(emission,'original_observers',lambda *args:observers)
    monkeypatch.setattr(emission,'detect_fixed',lambda *args:observer['mask'])
    def signed_emissivity(rho,pressure):
        value=np.where(rho==1.,-1.,np.where(rho==2.,1.,.5))
        fields={key:value for convention in emission.CONVENTIONS for key in (convention,convention+'_before')}
        return fields,np.ones_like(rho),{'any':value<0,'raw_nonfinite':np.zeros(rho.shape,bool)}
    emission.integrate_native(now,zero,g,{angle:view},signed_emissivity)
    attribution,recoveries,paths,reports=emission.finish_views({angle:view},g)
    assert attribution and recoveries and paths
    for row in attribution:
        assert row['observed_deficit_integral']==pytest.approx(sum(row[name] for name in
            ('cocoon_deficit_integral','moving_ambient_deficit_integral','external_deficit_integral','background_difference_integral')))
        assert row['brightness_positivity_pass'] is False
        assert row['cocoon_brightness_share'] is None
    assert max(row['error_to_scale'] for row in reports[str(angle)]['closure'].values())<2e-14
    assert np.any(view.maps['deficit_retained_linear_A_v100']<0)
    assert np.any(view.maps['deficit_retained_linear_C']>0)


def _lineage_fixture(tmp_path):
    snapshots={}
    epochs={}
    chain=[{'output_index':index} for index in range(51)]
    for index,role,epoch in [(0,'initial_h5','initial'),(20,'current_h5','current')]:
        path=tmp_path/f'data.{index:04d}.flt.h5';path.write_text(f'snapshot {index}')
        snapshots[role]=emission.budget._stat_identity(path)
        epochs[epoch]={'timestep':f'Timestep_{index}','time_code':float(index)}
        chain[index].update(snapshots[role]);chain[index].update(epochs[epoch])
    accepted={'schema_version':1,'status':'passed',
              'lineage':'accepted failed-run parent build/source plus validated 10 Myr home continuation',
              'snapshots':{'analysis_chain':chain}}
    path=tmp_path/'lineage.json';path.write_text(json.dumps(accepted))
    receipt={'inputs':snapshots,**epochs,'native_preflight':{
        'semantic_checks':{'inherited_parent_source_restart_and_chain':'passed'},
        'inherited_lineage':{'receipt':{'path':str(path),'sha256':emission.budget._sha256(path)}}}}
    return receipt,accepted,path


def test_verified_lineage_is_bound_without_hashing_native_or_restart_files(tmp_path,monkeypatch):
    receipt,_,path=_lineage_fixture(tmp_path)
    original=emission.budget._sha256
    def compact_only(source):
        assert source==path
        return original(source)
    monkeypatch.setattr(emission.budget,'_sha256',compact_only)
    assert emission.bind_inherited_lineage(receipt)['sha256']==original(path)


@pytest.mark.parametrize('fault',['absent','semantic','hash','status','lineage','chain','snapshot','time'])
def test_inherited_lineage_rejects_unaccepted_or_substituted_native_binding(tmp_path,fault):
    receipt,accepted,path=_lineage_fixture(tmp_path)
    if fault=='absent':receipt['native_preflight'].pop('inherited_lineage')
    elif fault=='semantic':receipt['native_preflight']['semantic_checks'].clear()
    elif fault=='hash':receipt['native_preflight']['inherited_lineage']['receipt']['sha256']='0'*64
    elif fault=='status':accepted['status']='pending'
    elif fault=='lineage':accepted['lineage']='unreviewed continuation'
    elif fault=='chain':accepted['snapshots']['analysis_chain'].pop()
    elif fault=='snapshot':Path(receipt['inputs']['current_h5']['path']).write_text('changed')
    elif fault=='time':accepted['snapshots']['analysis_chain'][20]['time_code']=40.
    if fault not in ('absent','semantic','hash'):
        path.write_text(json.dumps(accepted))
        receipt['native_preflight']['inherited_lineage']['receipt']['sha256']=emission.budget._sha256(path)
    with pytest.raises(ValueError,match='lineage|identity mismatch'):
        emission.bind_inherited_lineage(receipt)


def test_nondetection_is_specific_to_each_signed_solid_and_pooled_pair():
    g=grid();shape=(8,8,8);now=state(shape);zero=state(shape)
    mask=(g.z[:,None]>0)&(g.x[None,:]<0)
    observer={'mask':mask,'background':np.ones_like(mask,dtype=float)}
    view=emission.make_view(g,0,g.x,np.zeros_like(mask,dtype=float),{method:observer for method in emission.METHODS})
    rows,_=emission.integrate_native(now,zero,g,{0:view},fake_emissivity)
    for row in rows:
        absent=row['hemisphere']=='negative_z' or row['solid']=='W+'
        assert row['nondetection']==absent
        if absent:
            assert row['geometric_revolution_volume_kpc3']==0
            assert row['volume_kpc3_denominator']==0
            assert row['volume_kpc3_share'] is None
        else:
            assert row['geometric_revolution_volume_kpc3']>0
            assert row['volume_kpc3_denominator']>0


@pytest.mark.parametrize('axial_contact',[False,True])
def test_signed_solid_axial_contact_is_flagged_separately_from_radial_truncation(axial_contact):
    g=grid();shape=(8,8,8);now=state(shape);zero=state(shape)
    mask=np.zeros((8,8),bool);mask[7 if axial_contact else 5,2]=True
    observer={'mask':mask,'background':np.ones_like(mask,dtype=float)}
    view=emission.make_view(g,0,g.x,np.zeros_like(mask,dtype=float),{method:observer for method in emission.METHODS})
    rows,_=emission.integrate_native(now,zero,g,{0:view},fake_emissivity)
    for row in rows:
        assert not row['radial_domain_truncation']
        expected=axial_contact and row['solid']!='W+' and row['hemisphere']!='negative_z'
        assert row['axial_domain_truncation']==expected
        assert row['domain_truncation']==expected
