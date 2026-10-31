from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import numpy as np

import build_q032_selected_age_method_ladder as runner
import xray_cavity_method_ladder as ladder
import xray_cavity_synthetic as synthetic

AXES = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/xraise_grid_45deg")


def test_runner_rows_and_packed_masks_round_trip(tmp_path: Path) -> None:
    horizontal = np.loadtxt(AXES / "u_kpc.tsv")[::8]
    vertical = np.loadtxt(AXES / "z_kpc.tsv")[::8]
    rendered = synthetic.render_map(
        synthetic.load_atmosphere("group"), horizontal, vertical,
        synthetic.bipolar_pair(semiaxis_along_jet_kpc=40.0, semiaxis_across_jet_kpc=24.0),
        view_deg=45.0,
    )
    directory = tmp_path / "age_30" / "xraise_grid_45deg"
    directory.mkdir(parents=True)
    np.savetxt(directory / "xray_1kev_xraise_corrected_mjy_sr.tsv", rendered.surface_brightness, delimiter="\t")
    np.savetxt(directory / "tracer_max_los.tsv", rendered.cavity_mask.astype(float), delimiter="\t")
    np.savetxt(directory / "u_kpc.tsv", horizontal)
    np.savetxt(directory / "z_kpc.tsv", vertical)

    runner.run([("G-LO", 30, "45deg", directory)], tmp_path / "out")

    with (tmp_path / "out" / "method_ladder_rows.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 * 5
    seed = [row for row in rows if row["run"] == ladder.SEED_GROW]
    assert all(float(row["tracer_completeness"]) > 0.8 for row in seed)
    packed = np.load(tmp_path / "out" / "masks" / "G-LO_age30_45deg.npz")
    shape = tuple(packed["shape"])
    tracer = np.unpackbits(packed["tracer"])[: np.prod(shape)].reshape(shape).astype(bool)
    np.testing.assert_array_equal(tracer, rendered.cavity_mask)
    assert (tmp_path / "out" / "stamps" / "G-LO_age30_45deg.png").is_file()
