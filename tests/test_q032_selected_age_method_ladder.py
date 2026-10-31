from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import numpy as np
import pytest

import build_q032_selected_age_method_ladder as runner
import xray_cavity_method_ladder as ladder
import xray_cavity_synthetic as synthetic

AXES = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/xraise_grid_45deg")


def write_view(directory: Path, image: np.ndarray, tracer: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> Path:
    directory.mkdir(parents=True)
    np.savetxt(directory / "xray_1kev_xraise_corrected_mjy_sr.tsv", image, delimiter="\t")
    np.savetxt(directory / "tracer_max_los.tsv", tracer.astype(float), delimiter="\t")
    np.savetxt(directory / "u_kpc.tsv", horizontal)
    np.savetxt(directory / "z_kpc.tsv", vertical)
    return directory


def rendered_group(horizontal: np.ndarray, vertical: np.ndarray, cavities=()) -> synthetic.SyntheticMap:
    return synthetic.render_map(synthetic.load_atmosphere("group"), horizontal, vertical, cavities, view_deg=45.0)


def test_runner_rows_and_packed_masks_round_trip(tmp_path: Path) -> None:
    horizontal = np.loadtxt(AXES / "u_kpc.tsv")[::8]
    vertical = np.loadtxt(AXES / "z_kpc.tsv")[::8]
    rendered = rendered_group(
        horizontal, vertical, synthetic.bipolar_pair(semiaxis_along_jet_kpc=40.0, semiaxis_across_jet_kpc=24.0),
    )
    tracer_input = rendered.cavity_mask.astype(float)
    tracer_input[0, :3] = [
        np.nextafter(runner.TRACER_THRESHOLD, 0.0),
        runner.TRACER_THRESHOLD,
        np.nextafter(runner.TRACER_THRESHOLD, 1.0),
    ]
    directory = write_view(
        tmp_path / "age_30" / "xraise_grid_45deg", rendered.surface_brightness, tracer_input, horizontal, vertical,
    )

    runner.run([("G-LO", 30, "45deg", directory)], tmp_path / "out")

    with (tmp_path / "out" / "method_ladder_rows.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 * 5
    seed = [row for row in rows if row["run"] == ladder.SEED_GROW]
    assert all(float(row["tracer_completeness"]) > 0.8 for row in seed)
    packed = np.load(tmp_path / "out" / "masks" / "G-LO_age30_45deg.npz")
    shape = tuple(packed["shape"])
    tracer = np.unpackbits(packed["tracer"])[: np.prod(shape)].reshape(shape).astype(bool)
    expected_tracer = rendered.cavity_mask.copy()
    expected_tracer[0, :3] = [False, False, True]
    np.testing.assert_array_equal(tracer, expected_tracer)
    assert (tmp_path / "out" / "stamps" / "G-LO_age30_45deg.png").is_file()


def test_t0_baseline_adds_labelled_rungs_and_checks_axes(tmp_path: Path) -> None:
    horizontal = np.loadtxt(AXES / "u_kpc.tsv")[::8]
    vertical = np.loadtxt(AXES / "z_kpc.tsv")[::8]
    rendered = rendered_group(
        horizontal, vertical, synthetic.bipolar_pair(semiaxis_along_jet_kpc=60.0, semiaxis_across_jet_kpc=36.0),
    )
    null = rendered_group(horizontal, vertical)
    view = write_view(tmp_path / "view", rendered.surface_brightness, rendered.cavity_mask, horizontal, vertical)
    baseline = write_view(tmp_path / "t0", null.surface_brightness, null.cavity_mask, horizontal, vertical)

    metadata = runner.run([("G-HI", 20, "45deg", view)], tmp_path / "out", {("group", "45deg"): baseline})

    assert "seed_grow_goal045_t0_baseline" in metadata["runs"]
    assert "deficit_threshold_observer_radial_t0_calibrated" in metadata["runs"]
    with (tmp_path / "out" / "method_ladder_rows.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 * 9
    seed = [row for row in rows if row["run"] == "seed_grow_goal045_t0_baseline"]
    assert all(float(row["tracer_completeness"]) > 0.95 for row in seed)
    assert b"\r\n" not in (tmp_path / "out" / "method_ladder_rows.csv").read_bytes()

    shifted = write_view(tmp_path / "shifted", null.surface_brightness, null.cavity_mask, horizontal + 1.0, vertical)
    with pytest.raises(ValueError, match="baseline axes"):
        runner.run([("G-HI", 20, "45deg", view)], tmp_path / "out2", {("group", "45deg"): shifted})
