import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path('scripts/science').resolve()))
from build_q029_power_refresh import refreshed_geometry, add_factorization, SECONDS_PER_MYR
from build_four_case_cavity_age_method_comparison import build_cavity_powers


def test_geometry_change_rejects_clock_reuse():
    key=dict(case='C-HI',snapshot_index=10,view='90deg',side='negative_z',actual_time_myr=10)
    old=[dict(key,volume_kpc3=2,projected_cavity_radius_kpc=3)]
    new=[dict(key,volume_kpc3=2.01,centroid_radius_kpc=3,enthalpy_erg=5,pressure_dyn_cm2=1)]
    with pytest.raises(ValueError,match='volume_kpc3'):
        refreshed_geometry(old,new)


def test_side_power_uses_enthalpy_weighted_effective_age():
    key=dict(case='C-HI',snapshot_index=10,view='90deg',actual_time_myr=10)
    geom=[dict(key,side='negative_z',pV_erg=6e58/2.5),dict(key,side='positive_z',pV_erg=2e58/2.5)]
    age=[dict(key,age_method='sound_crossing_age',combined_age_myr=2,negative_side_age_myr=1,positive_side_age_myr=3,age_limit_direction='none',status='quantitative')]
    matched=[dict(key,observer_enthalpy_erg=8e58,native_lobe_enthalpy_erg=16e58,ratio_to_native_lobe_enthalpy=.5,injected_energy_erg=2e45*10*SECONDS_PER_MYR)]
    rows=add_factorization(build_cavity_powers(geom,age),matched)
    for row in rows:
        assert row['effective_bipolar_age_myr']==pytest.approx(1.2)
        assert row['factorization_relative_error']<1e-12
    assert rows[1]['inferred_cavity_power_erg_s']/rows[0]['inferred_cavity_power_erg_s']==pytest.approx(1.6)


@pytest.mark.parametrize('age,limit,status',[('', 'not_available','excluded'),(2,'upper_limit','censored')])
def test_limits_and_missing_ages_are_preserved(age,limit,status):
    key=dict(case='C-HI',snapshot_index=10,view='90deg',actual_time_myr=10)
    geom=[dict(key,side='negative_z',pV_erg=1e58),dict(key,side='positive_z',pV_erg=1e58)]
    ages=[dict(key,age_method='spectral_age_mean_pressure',combined_age_myr=age,age_limit_direction=limit,status=status)]
    matched=[dict(key,observer_enthalpy_erg=5e58,native_lobe_enthalpy_erg=1e59,ratio_to_native_lobe_enthalpy=.5,injected_energy_erg=2e45*10*SECONDS_PER_MYR)]
    rows=add_factorization(build_cavity_powers(geom,ages),matched)
    for row in rows:
        assert row['power_limit_direction']==('not_available' if age=='' else 'lower_limit')
        if age=='': assert row['effective_bipolar_age_myr']==row['inferred_cavity_power_erg_s']==''
