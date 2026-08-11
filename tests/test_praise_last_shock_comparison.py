from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from plutokore.radio import praise2


SCRIPT = Path("scripts/science/diagnose_praise_last_shock_comparison.py")


def load_module():
    spec = importlib.util.spec_from_file_location("diagnose_praise_last_shock_comparison", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_latest_shock_index_uses_endpoint_latest_shock():
    module = load_module()
    times = np.arange(6, dtype=float)
    last_shock = np.array([0.0, 1.0, 1.0, 3.2, 3.2, 3.2])
    assert module.latest_shock_index(times, last_shock) == 4


def test_smoothing_scope_separates_retained_stencil_contamination():
    module = load_module()
    times = np.arange(8, dtype=float)
    last_shock = np.full(8, 3.0)
    pressure = np.array([100.0, 100.0, 100.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    scope = module.smoothing_scope(pressure, times, last_shock)
    assert scope["shock_index_local"] == 3
    assert scope["retained_stencil_contaminated"] is True
    assert scope["retained_contaminated_count"] > 0


def test_representative_selection_is_deterministic_and_covers_core_regimes():
    module = load_module()
    rows = []
    for index in range(20):
        rows.append(
            {
                "physical_id": str(1000 + index),
                "unsmoothed_full_0.15GHz": str(10.0 ** (index - 10)),
                "history_length": str(10 + index),
                "shock_age": str(index),
                "pressure_dynamic_range_log10": str(index / 3),
                "log_endpoint_relative_difference": str((index - 10) / 100),
                "affected_linear_sg": str(index % 2 == 0),
                "shock_relative_state": (
                    "post_injection_recent" if index < 10 else "post_injection_older"
                ),
            }
        )
    first = module.select_representative_particles(rows, target=12)
    second = module.select_representative_particles(rows, target=12)
    assert first == second
    assert len({int(row["physical_id"]) for row in first}) == 12
    reasons = ";".join(row["panel_reason"] for row in first)
    for required in (
        "bright",
        "faint",
        "long_history",
        "short_history",
        "old_shock",
        "recent_shock",
        "smoothing_affected_true_intermediate",
        "smoothing_affected_false_intermediate",
    ):
        assert required in reasons


def test_run_praise2_actual_single_fails_if_requested_timestep_is_not_retained(monkeypatch):
    module = load_module()
    raw = {
        "physical_ids": np.array([42]),
        "time": np.arange(4, dtype=float),
        "pressure": np.ones((1, 4)),
        "density": np.ones((1, 4)),
        "tracer": np.ones((1, 4)),
        "last_shock_time": np.ones((1, 4)),
    }
    monkeypatch.setattr(module.praise2_driver, "_praise2_uniform_indices", lambda *_: np.array([0, 2, 3]))
    with pytest.raises(module.LastShockDiagnosticError, match="requested evaluation timestep"):
        module._run_praise2_actual_single(
            raw,
            0,
            object(),
            frequencies_ghz=np.array([0.15, 1.4]),
            evaluation_global_indices=[1, 3],
            window_width=5,
        )


def test_run_praise2_actual_single_uses_lossless_singleton_convention(monkeypatch):
    module = load_module()
    contract = {"part_data": {"pressure": np.ones((1, 1))}}
    monkeypatch.setattr(module, "_single_particle_contract", lambda *_: (contract, 3))
    monkeypatch.setattr(
        module.praise2_driver,
        "_praise2_uniform_indices",
        lambda *_: np.array([0]),
    )
    observed = {}

    def fake_kwargs(*_, losses, **__):
        observed["losses"] = losses
        return {}

    class FakePraise2:
        @staticmethod
        def praise(**kwargs):
            observed["emit_outputs"] = kwargs["emit_outputs"]
            values = np.array([[[3.0], [4.0]]]) * module.EMISSIVITY_UNIT
            return {
                "lossless": [{"part_output": 0, "emis": values}],
                "full": [{"part_output": 0, "emis": values * 0}],
            }

    monkeypatch.setattr(module, "build_praise2_call_kwargs", fake_kwargs)
    result = module._run_praise2_actual_single(
        {},
        0,
        FakePraise2(),
        frequencies_ghz=np.array([0.15, 1.4]),
        evaluation_global_indices=[3],
        window_width=5,
    )
    assert observed == {"losses": (0,), "emit_outputs": [0]}
    np.testing.assert_allclose(result[3], [3.0, 4.0])


def test_goal050_comparator_retains_cutoff_and_nonfinite_states():
    module = load_module()
    stable = {
        "trajectory": np.array([[[np.nan, np.nan], [10.0, 20.0]]]),
        "state": np.array(
            [[
                [module.stable_full.STATE_PHYSICAL_CUTOFF, module.stable_full.STATE_FINITE],
                [module.stable_full.STATE_FINITE, module.stable_full.STATE_FINITE],
            ]]
        ),
    }
    result = module._goal050_stable_emissivity(
        stable,
        np.array([10.0, np.nan]),
        np.array([5.0 / 3.0, 5.0 / 3.0]),
        np.array([1.0, 1.0]),
        0,
        0.8,
        frequencies=[0.15, 1.4],
    )
    assert result["values"][0] == 0.0
    assert np.isnan(result["values"][1])
    assert result["policies"] == [
        "explicit_cutoff_zero",
        "unavailable_nonfinite_gamma",
    ]


@pytest.mark.parametrize("window_width", [0, 5])
def test_instrumented_replay_matches_pinned_praise2_after_irregular_resampling(
    window_width,
):
    module = load_module()
    step_code = float((0.01 * u.Myr).to_value(u.s)) / module.workflow.TIME_UNIT_S
    times = np.array([499.0, 500.0, 500.6, 501.1, 502.1]) * step_code
    raw = {
        "physical_ids": np.array([42]),
        "time": times,
        "pressure": np.array([[np.nan, 1.0e-6, 1.1e-6, 0.9e-6, 1.2e-6]]),
        "density": np.array([[np.nan, 1.0e-4, 0.9e-4, 1.1e-4, 1.0e-4]]),
        "tracer": np.array([[np.nan, 0.8, 0.8, 0.8, 0.8]]),
        "last_shock_time": np.array(
            [[np.nan, times[3], times[3], times[3], times[3]]]
        ),
    }
    series = module._prepare_praise2_series(
        raw, 0, praise2, window_width=window_width
    )
    np.testing.assert_array_equal(series["source_local_indices"], [0, 2, 3])
    np.testing.assert_array_equal(series["source_global_indices"], [1, 3, 4])
    np.testing.assert_allclose(
        series["time_absolute"],
        times[[1, 3, 4]] * module.workflow.TIME_UNIT_S / module.TIME_MYR_S,
    )
    actual = module._run_praise2_actual_single(
        raw,
        0,
        praise2,
        frequencies_ghz=np.array([0.15, 1.4]),
        evaluation_global_indices=[4],
        window_width=window_width,
    )[4]
    replay = module.replay_praise2(
        praise2,
        series,
        evaluation_index=2,
        frequencies_ghz=np.array([0.15, 1.4]),
    )
    assert np.all(actual > 0)
    np.testing.assert_allclose(replay["emissivity"], actual, rtol=1e-8, atol=0.0)
    assert replay["classification"] == "finite"
