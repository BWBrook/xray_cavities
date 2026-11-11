from __future__ import annotations

import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

SCIENCE = Path(__file__).resolve().parents[1] / 'scripts/science'
sys.path.insert(0, str(SCIENCE))
import extract_fixed_box_energy_budget as fixed
import extract_spherical_energy_budget as native
from test_spherical_energy_budget import _base_state, _inputs, _velocity_code


def _run(tmp_path, current=None, initial=None, **options):
    initial_path, current_path, environment = _inputs(tmp_path, current, initial)
    output = tmp_path/'fixed.json'
    result = fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current_path,
        initial_h5=initial_path,environment_path=environment,output=output,inset_kpc=1.,**options)
    return result, (initial_path,current_path,environment), output


def _receipt(tmp_path, paths, **changes):
    initial,current,environment = paths
    result = {'schema_version':1,'status':'bound_spherical_budget_inputs','case':'C-LO','snapshot_index':1,
        'initial':{'timestep':'Timestep_0','time_code':0.},
        'current':{'timestep':'Timestep_1','time_code':2.*native.CODE_TIME_PER_MYR},
        'inputs':{name:{**native._stat_identity(path),'sha256':native._sha256(path)} for name,path in
                  (('initial_h5',initial),('current_h5',current),('environment',environment))}}
    result.update(changes)
    path=tmp_path/'receipt.json';path.write_text(json.dumps(result))
    return path


def test_mass_partitions_use_current_binary_full_cells_and_same_initial_cells(tmp_path):
    initial=_base_state();current={k:v.copy() for k,v in initial.items()}
    current['rho'][2,2,3]=3.;current['tr1'][2,2,3]=.002
    current['rho'][2,3,2]=1.;current['tr1'][2,3,2]=.001
    current['prs'][2,2,3]+=2.
    result,_,_=_run(tmp_path,current,initial)
    box=result['regions']['fixed_inset_box'];parts=box['partitions']
    assert parts['all']['cell_count']==27
    assert parts['cocoon']['cell_count']==1
    assert parts['cocoon']['initial_mass_g']==pytest.approx(2.*fixed.MASS_UNIT_G)
    assert parts['cocoon']['current_mass_g']==pytest.approx(3.*fixed.MASS_UNIT_G)
    assert parts['cocoon']['mass_delta_g']==pytest.approx(fixed.MASS_UNIT_G)
    assert parts['ambient']['mass_delta_g']==pytest.approx(-fixed.MASS_UNIT_G)
    assert parts['all']['mass_delta_g']==0.
    assert box['partition_identity']['pass']
    assert parts['cocoon']['thermal_delta_erg']==pytest.approx(2.*native.UNIT_ENERGY_ERG/(native.GAMMA_GAS-1.))
    assert parts['all']['total_delta_erg']==pytest.approx(parts['cocoon']['total_delta_erg']+parts['ambient']['total_delta_erg'])


def test_potential_shift_response_is_mass_delta_not_an_invariant_energy_share(tmp_path):
    current=_base_state();current['rho'][2,2,3]+=1.;current['tr1'][2,2,3]=.1
    current['rho'][2,3,2]-=.5
    shift=-4.7e14
    result,_,_=_run(tmp_path,current,potential_zero_shift_cm2_s2=shift)
    parts=result['regions']['fixed_inset_box']['partitions']
    for name in fixed.REGIONS:
        p=parts[name]
        assert p['gravitational_shifted_delta_erg']==pytest.approx(p['gravitational_delta_erg']+shift*p['mass_delta_g'])
        assert p['potential_zero_shift']['identity_pass']
        assert p['thermal_plus_kinetic_delta_erg']==p['thermal_delta_erg']+p['kinetic_delta_erg']
    assert parts['all']['mass_delta_g']==pytest.approx(.5*fixed.MASS_UNIT_G)
    assert parts['all']['gravitational_shifted_delta_erg']!=pytest.approx(parts['all']['gravitational_delta_erg'])


def test_full_cell_box_membership_disturbance_contact_and_omitted_energy(tmp_path):
    current=_base_state()
    current['vx1'][2,2,3]=_velocity_code(30.)
    current['prs'][2,2,4]+=1.
    current['tr1'][2,2,4]=.02
    result,_,_=_run(tmp_path,current)
    assert result['fixed_box_cell_faces_kpc']=={'x':[-1.5,1.5],'y':[-1.5,1.5],'z':[-1.5,1.5]}
    assert result['regions']['fixed_inset_box']['partitions']['all']['cell_count']==27
    thermo=result['operational_coverage']['thermodynamic_ge_1pct']
    assert thermo['outside_fixed_inset_box']['cell_count']==1
    assert thermo['outside_fixed_inset_box']['thermal_delta_erg']==pytest.approx(native.UNIT_ENERGY_ERG/(native.GAMMA_GAS-1.))
    assert thermo['all_selected_cells_inside_fixed_inset_box'] is False
    assert thermo['contacts_domain_face'] is True
    assert result['operational_coverage']['speed_ge_30_km_s']['contacts_inset_boundary'] is True
    assert result['operational_coverage']['speed_ge_100_km_s']['extent']['cell_count']==0
    assert result['operational_coverage']['current_cocoon']['outside_fixed_inset_box']['cell_count']==1
    assert result['fixed_box_partition_identity']['pass']
    assert result['scientific_qualification']['qualified'] is False


def test_partial_boundary_cells_are_excluded_even_with_centres_inside(tmp_path):
    state=_base_state();state['vx1'][2,2,3]=_velocity_code(110.)
    paths=_inputs(tmp_path,state);initial,current,environment=paths
    result=fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current,initial_h5=initial,
        environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.1)
    assert result['regions']['fixed_inset_box']['partitions']['all']['cell_count']==1
    assert result['fixed_box_cell_faces_kpc']['x']==[-.5,.5]
    assert result['fixed_box_nominal_inscribed_radius_kpc']==pytest.approx(1.4)
    assert result['fixed_box_retained_cell_inscribed_radius_kpc']==pytest.approx(.5)
    assert result['speed_apertures']['R100']['geometrically_complete_in_fixed_inset_box'] is False


def test_mass_budgets_reproduce_existing_r100_r300_energy_definitions(tmp_path):
    initial=_base_state();current={k:v.copy() for k,v in initial.items()}
    current['vx1'][2,2,4]=_velocity_code(110.)
    current['vx3'][2,2,3]=_velocity_code(310.)
    current['rho'][2,2,3]+=1.
    current['tr1'][2,2,3]=.1
    current['prs'][2,2,2]+=2.
    result,paths,_=_run(tmp_path,current,initial)
    initial_h5,current_h5,environment=paths
    old=native.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current_h5,initial_h5=initial_h5,
        environment_path=environment,output=tmp_path/'sphere.json',safe_buffer_kpc=1.)
    for threshold in ('100','300'):
        parts=result['regions']['R'+threshold]['partitions']
        reference=old['thresholds'][threshold]['sphere_budget']
        for region in fixed.REGIONS:
            expected=reference['delta_erg'] if region=='all' else reference['current_binary_partition'][region]
            for key in (*native.COMPONENTS,'total'):
                assert parts[region][key+'_delta_erg']==pytest.approx(expected[key+'_delta_erg'])
    assert result['speed_apertures']['R100']['geometrically_complete_in_fixed_inset_box'] is False
    assert result['speed_apertures']['R300']['geometrically_complete_in_fixed_inset_box'] is True


def test_bound_receipt_and_all_source_inputs_are_recorded(tmp_path):
    paths=_inputs(tmp_path,_base_state());initial,current,environment=paths
    receipt=_receipt(tmp_path,paths)
    result=fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current,initial_h5=initial,
        environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.,input_receipt=receipt)
    assert result['provenance']['mode']=='bound_input_receipt'
    assert len(result['provenance']['source_files'])==len(fixed.SOURCE_FILES)
    assert result['provenance']['input_receipt_claims']['case']=='C-LO'
    assert result['speed_apertures']['R100']['available'] is False
    assert 'R100' not in result['regions']
    with pytest.raises(ValueError,match='overwrite'):
        fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current,initial_h5=initial,
            environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.,input_receipt=receipt)


@pytest.mark.parametrize('change',('case','time','mutation'))
def test_receipt_mismatch_and_mutated_native_input_rejected(tmp_path,change):
    paths=_inputs(tmp_path,_base_state());initial,current,environment=paths
    receipt=_receipt(tmp_path,paths)
    if change=='mutation':
        with current.open('ab') as stream:stream.write(b'mutated')
    else:
        payload=json.loads(receipt.read_text())
        if change=='case':payload['case']='G-LO'
        else:payload['current']['time_code']=3.*native.CODE_TIME_PER_MYR
        receipt.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='receipt'):
        fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current,initial_h5=initial,
            environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.,input_receipt=receipt)
    assert not (tmp_path/'fixed.json').exists()


def test_grid_mismatch_and_excluded_ghi_fail_without_publishing(tmp_path):
    paths=_inputs(tmp_path,_base_state());initial,current,environment=paths
    with h5py.File(current,'a') as h5:h5['node_coords/X'][2] += .05
    with pytest.raises(ValueError,match='cell centres disagree'):
        fixed.extract_snapshot(case='C-LO',snapshot_index=1,current_h5=current,initial_h5=initial,
            environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.)
    with pytest.raises(ValueError,match='excluded'):
        fixed.extract_snapshot(case='G-HI',snapshot_index=48,current_h5=current,initial_h5=initial,
            environment_path=environment,output=tmp_path/'fixed.json',inset_kpc=1.)
    assert not (tmp_path/'fixed.json').exists()
