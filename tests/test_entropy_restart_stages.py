import csv
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import reduce_entropy_restart_stages as rk


def raw_rows():
    rows = []
    times = (3000., 3000.5, 3002., 3005.)
    for j in range(3):
        for stage, weight in enumerate(rk.WEIGHTS, 1):
            for shell in ("injector_flag", "r_0.75_5"):
                row = dict(step=41+j, time_start_code=times[j], time_end_code=times[j+1],
                           dt_code=times[j+1]-times[j], entropy_switch="selective", stage=stage,
                           rk_weight=weight, radius_kpc=shell, tracer_fraction="f_gt_0.5",
                           energy_unit_erg=rk.NATIVE_UNIT_ERG, **dict.fromkeys(rk.METRICS, 0))
                row.update(cell_visits=1, entropy_visits=1)
                if shell == "r_0.75_5":
                    if stage == 1:
                        row.update(raw_entropy_gain=2, raw_cell_gain=2)
                    else:
                        # The two changes at one visit partially cancel before the cell total.
                        row.update(gas_energy_floors=1, raw_E_floor_gain=1, raw_entropy_loss=-4,
                                   raw_cell_loss=-3)
                row["effective_net_code"] = weight * (row["raw_cell_gain"] + row["raw_cell_loss"])
                row["effective_cell_gross_code"] = weight * (row["raw_cell_gain"] - row["raw_cell_loss"])
                rows.append(row)
    return rows


def read(rows, times=(3000., 3002., 3005.)):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return rk.read_ledger(buf, times=times, steps=[41, 43, 44], setting="selective", physical_cells=2)


def test_actual_output_steps_weights_and_signed_events():
    cubes, info = read(raw_rows())
    rows = list(rk.make_rows("G-HI", "ON", [10, 11, 12], [3000, 3002, 3005], [41, 43, 44], cubes, info))
    ext = [r for name, r in rows if name == "rk_interval_regions.csv" and r["region"] == "exterior"]
    net = next(r for name, r in rows if name == "rk_window_regions.csv" and r["region"] == "exterior")
    assert [r["cell_visits"] for r in ext] == [4, 2]
    assert net["cell_visits"] == 6 and net["gas_energy_floors"] == 3
    assert net["E_floor_gain_erg"] / rk.NATIVE_UNIT_ERG == pytest.approx(3)
    assert net["entropy_gain_erg"] / rk.NATIVE_UNIT_ERG == pytest.approx(3)
    assert net["entropy_loss_erg"] / rk.NATIVE_UNIT_ERG == pytest.approx(-12)
    assert net["effective_net_erg"] / rk.NATIVE_UNIT_ERG == pytest.approx(-6)
    assert net["effective_cell_gross_erg"] / rk.NATIVE_UNIT_ERG == pytest.approx(12)
    assert net["effective_net_over_label"] == pytest.approx(
        sum(r["effective_net_erg"] for r in ext) / sum(r["labelled_energy_erg"] for r in ext))
    assert net["effective_net_over_label"] != pytest.approx(sum(r["effective_net_over_label"] for r in ext)/2)
    assert info["flagged_cells_per_stage"] == [1]


def test_a_step_cannot_be_reassigned_across_an_output_boundary():
    with pytest.raises(ValueError, match="output time and step"):
        read(raw_rows(), times=(3000., 3000.5, 3005.))


def test_equal_cell_total_cannot_hide_a_duplicate_spatial_bin():
    rows = raw_rows()
    rows[1]["radius_kpc"] = rows[0]["radius_kpc"]
    with pytest.raises(ValueError, match="duplicate"):
        read(rows)
