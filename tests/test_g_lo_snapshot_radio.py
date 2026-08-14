from pathlib import Path
import sys

import h5py
import numpy as np
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.g_lo_snapshot_radio import (
    EMISSIVITY_UNIT,
    align_particle_ids,
    audit_branch_entry,
    effective_start_columns,
    luminosity_from_map,
    run_praise_group,
)


def test_effective_starts_use_history_record_count() -> None:
    plan = {
        "effective_history_records": np.array([5, 3, 0]),
        "active_mask": np.array([True, True, False]),
    }
    assert effective_start_columns(plan, 5).tolist() == [0, 2, -1]


def test_branch_audit_fails_future_source() -> None:
    entry = {
        "emis": np.ones((2, 5, 1)) * EMISSIVITY_UNIT,
        "part_output": 3,
    }
    try:
        audit_branch_entry(entry, rows=2, target_relative=2)
    except RuntimeError as exc:
        assert "future particle" in str(exc)
    else:
        raise AssertionError("future source output was accepted")


def test_particle_id_alignment_preserves_requested_order() -> None:
    parsed = np.array([30, 10, 20])
    desired = np.array([20, 30])
    assert align_particle_ids(parsed, desired).tolist() == [2, 0]


def test_luminosity_is_four_pi_intensity_area() -> None:
    values = np.ones((2, 3, 4))
    actual = luminosity_from_map(values, pixel_size_kpc=2.0)
    expected = 4.0 * np.pi * 6.0 * (2.0 * 3.0856775814913673e19) ** 2
    np.testing.assert_allclose(actual, np.full(4, expected))


def test_group_uses_external_singleton_convention(tmp_path: Path) -> None:
    path = tmp_path / "history.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("times", data=np.array([0.0, 1.0, 2.0]))
        h5.create_dataset("endpoint_ids", data=np.array([7]))
        for name, values in {
            "pressure": [[np.nan, 2.0, 3.0]],
            "density": [[np.nan, 1.0, 1.0]],
            "tracer": [[np.nan, 0.5, 0.5]],
            "last_shock_time": [[np.nan, 1.0, 1.0]],
        }.items():
            h5.create_dataset(name, data=np.asarray(values))

    class FakePraise2:
        @staticmethod
        def praise(**kwargs):
            entries_lossless = []
            entries_full = []
            rows = kwargs["part_data"]["pressure"].shape[0]
            for output in kwargs["emit_outputs"]:
                entries_lossless.append(
                    {
                        "emis": np.ones((rows, 5, 1)) * EMISSIVITY_UNIT,
                        "part_output": output,
                    }
                )
                entries_full.append(
                    {
                        "emis": np.full((rows, 5, 1), 2.0) * EMISSIVITY_UNIT,
                        "part_output": output,
                    }
                )
            return {"lossless": entries_lossless, "full": entries_full}

    with h5py.File(path, "r") as h5:
        result = run_praise_group(
            h5=h5,
            rows=np.array([0]),
            start_column=1,
            target_columns=[1, 2],
            praise2=FakePraise2(),
        )
    np.testing.assert_array_equal(result[1]["full"], result[1]["lossless"])
    assert result[1]["singleton_external_convention"] is True
    np.testing.assert_array_equal(result[2]["full"], np.full((1, 5), 2.0))
    assert result[2]["source_column"] == 2
