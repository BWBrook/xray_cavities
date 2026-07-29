from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from plutokore.radio.praise import get_K, get_emissivity_numba
from plutokore.radio.raytracing import raytrace_particles_multiple_freq


SCRIPT = Path("scripts/science/g_lo_radio_method_value.py")


def load_module():
    spec = importlib.util.spec_from_file_location("g_lo_radio_method_value", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def praise_fixture(n=4, times=6):
    t = np.arange(1, times + 1, dtype=float) * 1.0e13
    ids = np.array([101, 407, 900, 1503][:n], dtype=np.int64)
    pressure = np.array([(1.0 + 0.03 * i) * (1.0 + 0.02 * np.arange(times)) for i in range(n)]) * 1e-10
    density = np.ones((n, times)) * 1e-21
    tracer = np.ones((n, times)) * 0.8
    last = np.zeros((n, times, 3))
    last[:, :, 1] = t[0] * 0.5
    return {
        "physical_ids": ids,
        "pressure": pressure,
        "density": density,
        "tracer": tracer,
        "last_shock_time": last,
        "time": t,
        "tinj": t[0] - 0.25e13 + np.zeros(n),
    }


def test_praise_adapter_uses_actual_function_and_final_column():
    m = load_module()
    result = m.calculate_praise_pair(praise_fixture(), frequencies=[0.15, 1.4])
    assert result["ids"].tolist() == [101, 407, 900, 1503]
    assert result["metadata"]["time_index"] == 5
    assert result["full"].shape == (4, 2)
    assert np.all(np.isfinite(result["full"].value))
    assert np.all(result["full"].value <= result["none"].value * (1 + 1e-10))


def test_actual_praise_full_branch_can_exceed_none_under_compression():
    m = load_module()
    cache = praise_fixture(n=1, times=6)
    cache["pressure"][0] = np.linspace(1.0, 2.0, 6) * 1e-10
    result = m.calculate_praise_pair(
        cache,
        frequencies=[0.15, 1.4],
        include_adiabatic=True,
    )
    ratios = result["full"].value[0] / result["none"].value[0]
    assert ratios[0] > 1.0
    assert ratios[1] < 1.0
    assert np.all(result["full"].value <= result["adiabatic"].value * (1 + 1e-10))
    assert result["metadata"]["loss_branches"] == ["full", "adiabatic", "none"]


def test_praise_adapter_rejects_nonfinite_and_nonmonotonic_history():
    m = load_module()
    bad = praise_fixture()
    bad["pressure"][0, 2] = np.nan
    with pytest.raises(ValueError, match="pressure.*(finite|internal)"):
        m.calculate_praise_pair(bad)
    bad = praise_fixture()
    bad["time"][2] = bad["time"][1]
    with pytest.raises(ValueError, match="strictly increasing"):
        m.calculate_praise_pair(bad)


def test_pressure_modes_are_explicit_positive_and_ids_are_preserved():
    m = load_module()
    result = m.calculate_praise_pair(praise_fixture(), pressure_mode="log_savgol")
    assert result["metadata"]["pressure_mode"] == "log_savgol"
    assert result["metadata"]["pressure_smoothing_window"] == 5
    assert result["metadata"]["pressure_smoothing_polyorder"] == 3
    assert np.all(result["full"].value >= 0)
    assert result["ids"].tolist() == [101, 407, 900, 1503]


def test_pressure_mode_rejects_linear_or_boolean_smoothing() -> None:
    m = load_module()
    with pytest.raises(ValueError, match="linear-domain smoothing is prohibited"):
        m.calculate_praise_pair(praise_fixture(), pressure_mode="linear_savgol")
    with pytest.raises(TypeError, match="smooth_pressure"):
        m.calculate_praise_pair(praise_fixture(), smooth_pressure=True)


def test_short_log_savgol_history_is_unchanged() -> None:
    m = load_module()
    cache = praise_fixture(n=1, times=4)
    data, _, _, metadata = m._normalise_cache(cache, pressure_mode="log_savgol")
    np.testing.assert_array_equal(data["pressure"], cache["pressure"])
    assert metadata["short_history_rows_left_unsmoothed"] == 1


def test_leading_preinjection_nan_prefix_is_preserved_and_endpoint_is_finite():
    m = load_module()
    cache = praise_fixture()
    cache["pressure"][0, :2] = np.nan
    cache["density"][0, :2] = np.nan
    cache["tracer"][0, :2] = np.nan
    cache["last_shock_time"][0, :2, :] = np.nan
    cache["last_shock_time"][0, 2:, 1] = cache["time"][2] - 0.5e13
    result = m.calculate_praise_pair(cache)
    assert np.all(np.isfinite(result["full"].value))
    assert result["metadata"]["injection_prefix_lengths"][0] == 2
    assert result["metadata"]["pre_injection_handling"] == "trimmed_per_first_present_output"
    assert result["metadata"]["injection_group_count"] == 2
    cache["pressure"][0, 3] = np.nan
    with pytest.raises(ValueError, match="internal/post-injection"):
        m.calculate_praise_pair(cache)


def test_preinjection_trim_matches_direct_short_history():
    m = load_module()
    cache = praise_fixture()
    for key in ("pressure", "density", "tracer"):
        cache[key][0, :2] = np.nan
    cache["last_shock_time"][0, :2, :] = np.nan
    cache["last_shock_time"][0, 2:, 1] = cache["time"][2] - 0.5e13
    grouped = m.calculate_praise_pair(cache)
    short = {
        "physical_ids": cache["physical_ids"][:1],
        "time": cache["time"][2:],
        "pressure": cache["pressure"][:1, 2:],
        "density": cache["density"][:1, 2:],
        "tracer": cache["tracer"][:1, 2:],
        "last_shock_time": cache["last_shock_time"][:1, 2:, :],
    }
    direct = m.calculate_praise_pair(short)
    np.testing.assert_allclose(grouped["full"][0].value, direct["full"][0].value)
    np.testing.assert_allclose(grouped["none"][0].value, direct["none"][0].value)
    assert grouped["metadata"]["tinj"][0] == cache["tinj"][0]
    assert grouped["metadata"]["effective_start_time"][0] == cache["time"][2]
    assert grouped["metadata"]["effective_start_delay"][0] == pytest.approx(
        cache["time"][2] - cache["tinj"][0]
    )


def singleton_fixture():
    cache = praise_fixture(n=1, times=2)
    for field in ("pressure", "density", "tracer"):
        cache[field][0, 0] = np.nan
    cache["last_shock_time"][0, 0, :] = np.nan
    cache["last_shock_time"][0, 1, 1] = cache["time"][1]
    cache["tinj"][0] = cache["time"][0]
    return cache


def test_single_record_history_is_fail_closed_without_explicit_policy():
    m = load_module()
    with pytest.raises(ValueError, match="single-record"):
        m.calculate_praise_pair(singleton_fixture())


def test_single_record_instantaneous_policy_matches_direct_emissivity():
    m = load_module()
    cache = singleton_fixture()
    result = m.calculate_praise_pair(
        cache,
        singleton_policy="instantaneous_recent_shock",
    )
    full = result["full"].to_value(u.W / (u.Hz * u.m**3 * u.sr))
    none = result["none"].to_value(u.W / (u.Hz * u.m**3 * u.sr))
    np.testing.assert_array_equal(full, none)
    assert np.all(np.isfinite(full))
    assert result["metadata"]["single_record_instantaneous_count"] == 1
    assert result["metadata"]["singleton_policy"] == "instantaneous_recent_shock"

    pressure = cache["pressure"][:, -1]
    density = cache["density"][:, -1]
    tracer = cache["tracer"][:, -1]
    gamma_c = m.get_adiabatic_eff(pressure, density)
    frequency_si = (np.array([0.15, 1.4]) * u.GHz).si.value * 1.05
    current_gamma = m.get_gamma_larmor_numba(
        freq=frequency_si,
        eta=0.03,
        p=pressure,
        gamma_c=gamma_c,
    )
    expected = get_emissivity_numba(
        s=2.2,
        freq=frequency_si,
        eta=0.03,
        gamma_c=gamma_c,
        p=pressure,
        p_inj=pressure,
        gm=current_gamma,
        gm_inj=current_gamma,
        tracer=tracer,
        K=get_K(2.2, gamma_c, 500.0, 1e5),
    )
    np.testing.assert_allclose(full, expected, rtol=1e-13, atol=0.0)


def test_single_record_policy_rejects_stale_shock():
    m = load_module()
    cache = singleton_fixture()
    cache["last_shock_time"][0, 1, 1] = cache["time"][0] - 1.0
    with pytest.raises(ValueError, match="recent-shock"):
        m.calculate_praise_pair(
            cache,
            singleton_policy="instantaneous_recent_shock",
        )


def test_injection_time_must_not_follow_effective_history_start():
    m = load_module()
    cache = praise_fixture()
    cache["tinj"][0] = cache["time"][1]
    with pytest.raises(ValueError, match="tinj"):
        m.calculate_praise_pair(cache)


def two_lobe_fixture():
    left = np.array([[x, y, z] for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)])
    right = left + np.array([10.0, 0.0, 0.0])
    return np.vstack((left, right)), np.ones((16, 3)) * 1e-6, np.r_[np.zeros(8, int), np.ones(8, int)]


def test_component_raytrace_keeps_disconnected_gap_dark_and_converts_units():
    m = load_module()
    coords, vel, labels = two_lobe_fixture()
    grid = (np.arange(-1.0, 12.0, 1.0), np.arange(-1.0, 3.0, 1.0))
    out = m.raytrace_radio(
        coords=coords,
        vel_vec=vel,
        particle_emissivities=np.ones((16, 1)) * (u.W / (u.Hz * u.m**3 * u.sr)),
        grid=grid,
        ray_depth_lim=(-1.0, 2.0),
        component_labels=labels,
        delta_r=0.1,
        pixel_size_kpc=1.8,
    )
    assert out["metadata"]["component_count"] == 2
    assert out["metadata"]["path_length_units"] == "m"
    assert out["metadata"]["kpc_to_m"] == pytest.approx(m.KPC_TO_M)
    assert out["map"].unit.is_equivalent(u.W / (u.Hz * u.m**2 * u.sr))
    assert np.all(out["map"].value[5:8, :, :] == 0)
    repeat = m.raytrace_radio(
        coords=coords, vel_vec=vel, particle_emissivities=np.ones((16, 1)), grid=grid,
        ray_depth_lim=(-1.0, 2.0), component_labels=labels, delta_r=0.1, kd_jobs=2,
    )
    np.testing.assert_array_equal(out["map"].value, repeat["map"].value)
    assert out["metadata"]["kd_jobs"] == 1
    assert repeat["metadata"]["kd_jobs"] == 2
    # The current global Delaunay implementation bridges the synthetic gap;
    # the adapter's component-wise calls must not reproduce that artefact.
    global_map = raytrace_particles_multiple_freq(
        grid=grid, ray_depth_lim=(-1.0, 2.0), rot_mat=np.eye(3), delta_r=0.1,
        coords=coords, vel_vec=vel, obs_normal=np.array([0.0, 1.0, 0.0]),
        particle_emissivities=np.ones((16, 1)) * (u.W / (u.Hz * u.m**3 * u.sr)),
        s=2.2, dist_upper_bound=20.0, kd_jobs=1,
    )
    assert np.any(global_map.value[5:8, :, :] > 0)


def test_velocity_and_view_rotation_contract():
    m = load_module()
    coords, vel, labels = two_lobe_fixture()
    with pytest.raises(ValueError, match="norm < 1"):
        m.raytrace_radio(coords=coords, vel_vec=np.ones_like(vel), particle_emissivities=np.ones((16, 1)),
                         grid=(np.arange(2.0), np.arange(2.0)), ray_depth_lim=(-1, 2), component_labels=labels)
    result = m.raytrace_radio(coords=coords, vel_vec=vel, particle_emissivities=np.ones((16, 1)),
                              grid=(np.arange(2.0), np.arange(2.0)), ray_depth_lim=(-1, 2),
                              component_labels=labels, view_rotation_deg=90)
    np.testing.assert_allclose(result["metadata"]["rotation_matrix"], [[1, 0, 0], [0, 0, -1], [0, 1, 0]], atol=1e-12)
    np.testing.assert_allclose(result["metadata"]["physical_ray_normal"], [0, 0, -1], atol=1e-12)
    np.testing.assert_allclose(result["metadata"]["raytracer_obs_normal_input"], [0, -1, 0], atol=1e-12)
    assert result["metadata"]["doppler_normal_matches_cast_ray"] is True
    with pytest.raises(ValueError, match="kd_jobs"):
        m.raytrace_radio(
            coords=coords,
            vel_vec=vel,
            particle_emissivities=np.ones((16, 1)),
            grid=(np.arange(2.0), np.arange(2.0)),
            ray_depth_lim=(-1, 2),
            component_labels=labels,
            kd_jobs=0,
        )


def test_materiality_rule_and_repeatability():
    m = load_module()
    full = np.array([[0.0, 2.0], [0.0, 1.0]])
    none = np.ones((2, 2))
    one = m.compare_loss_maps(full, none, threshold=0.05)
    decision = m.evaluate_materiality([one, one, one], [[one, one]], numerical_error=0.01)
    assert decision["positive"] is True
    repeat = m.compare_loss_maps(full, none, threshold=0.05)
    for key, value in one.items():
        if np.isnan(value) if isinstance(value, float) else False:
            assert np.isnan(repeat[key])
        else:
            assert repeat[key] == value


def test_spectral_index_uses_positive_steep_alpha():
    m = load_module()
    freqs = [0.15, 1.4]
    full = np.ones((2, 3, 2))
    full[:, :, 1] = (1.4 / 0.15) ** -0.7
    none = np.ones((2, 3, 2))
    metrics = m.compare_loss_maps(full, none, frequencies=freqs)
    assert metrics["spectral_index_change"] == pytest.approx(0.7 - 0.0, abs=1e-12)


def _synthetic_replay(*, cutoff: bool = True, finite: bool = True):
    return {
        "ap_arr": np.array([[1.0]]),
        "a2_arr": np.array([[2.0]]),
        "current_lorentz": np.array([[4.0]]),
        "injection_lorentz": np.array([[3.0]]),
        "shocked_mask": np.array([[0, 0]]),
        "no_emission": np.array([[1 if cutoff else -1]]),
        "no_emission_mask": np.array([[cutoff]]),
        "particle_pressure": np.array([[5.0, 6.0]]),
        "injection_pressure": np.array([5.0]),
        "endpoint_tracer": np.array([0.8]),
        "finite_inputs_dynamics": np.array([finite]),
        "shock_assignment_valid": np.array([True]),
    }


def test_nonfinite_forensics_classifies_only_proven_full_loss_cutoffs():
    m = load_module()
    kwargs = dict(
        pressure_mode="unsmoothed", losses="full", start_index=2,
        rows=np.array([0]), physical_ids=np.array([407]),
        frequencies=np.array([1.4]), values=np.array([[np.nan]]),
        replay=_synthetic_replay(), matched_values=np.array([[1.0]]),
        returned_info={"ap_arr": np.array([[1.0]]), "a2_arr": np.array([[2.0]]),
                       "current_lorentz": np.array([[4.0]]),
                       "injection_lorentz": np.array([[3.0]])},
    )
    records = m._forensic_records(**kwargs)
    assert records[0]["classification"] == "proven_full_loss_cutoff"
    assert records[0]["physical_id"] == 407
    assert records[0]["output_class"] == "nan"

    for value, replay, matched, loss in [
        (np.inf, _synthetic_replay(), np.array([[1.0]]), "full"),
        (np.nan, _synthetic_replay(), None, "none"),
        (np.nan, _synthetic_replay(), np.array([[1.0]]), "full"),
    ]:
        if loss == "full" and np.isnan(value):
            replay = _synthetic_replay()
            replay["injection_lorentz"] = np.array([[99.0]])
        unresolved = m._forensic_records(
            **{**kwargs, "losses": loss, "values": np.array([[value]]),
               "replay": replay, "matched_values": matched}
        )
        assert unresolved[0]["classification"] == "unresolved_nonfinite"


def test_default_adapter_still_rejects_nonfinite_outputs(monkeypatch):
    m = load_module()
    original = m.calculate_praise_emissivity_numba

    def fake(**kwargs):
        n = kwargs["data_dict"]["id"].shape[0]
        nf = kwargs["frequencies"].size
        value = np.full((n, nf), np.nan if kwargs["losses"] == "full" else 1.0)
        info = {
            "ap_arr": np.zeros((n, kwargs["data_dict"]["time"].size - 1)),
            "a2_arr": np.zeros((n, kwargs["data_dict"]["time"].size - 1)),
            "injection_lorentz": np.ones((n, nf)),
        }
        return value * (u.W / (u.Hz * u.m**3 * u.sr)), info

    monkeypatch.setattr(m, "calculate_praise_emissivity_numba", fake)
    with pytest.raises(ValueError, match="non-finite endpoint emissivities"):
        m.calculate_praise_pair(praise_fixture(n=1))
    monkeypatch.setattr(m, "calculate_praise_emissivity_numba", original)


def test_diagnostic_finite_behavior_returns_compact_records():
    m = load_module()
    result = m.calculate_praise_pair(praise_fixture(n=1), diagnostic=True)
    diagnostics = result["nonfinite_diagnostics"]
    assert diagnostics["nonfinite"] is False
    assert diagnostics["record_count"] == 4
    assert diagnostics["unresolved_nonfinite_count"] == 0
    assert all(record["classification"] == "finite" for record in diagnostics["records"])
