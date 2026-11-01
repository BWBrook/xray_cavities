from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCIENCE = Path(__file__).resolve().parents[1] / "scripts" / "science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
import audit_nojet_controls as audit


class Potential:
    def potential_at_radius(self, radius):
        return np.asarray(radius) / audit.UNIT_LENGTH_CM * 1e13


def write_snapshot(path, *, time=0.0, edges=None, changes=()):
    if edges is None:
        edges = np.array([-150., -100., -40., 0., 20., 70., 150.])
    centres = (edges[:-1] + edges[1:]) / 2
    shape = (len(centres),) * 3
    with h5py.File(path, "w") as h5:
        for name in ("X", "Y", "Z"):
            h5.create_dataset(f"cell_coords/{name}", data=centres)
            h5.create_dataset(f"node_coords/{name}", data=edges)
        group = h5.create_group("Timestep_0")
        group.attrs["Time"] = time
        variables = group.create_group("vars")
        for name in audit.FIELDS:
            variables.create_dataset(name, data=np.full(shape, 2. if name in ("rho", "prs") else 0.))
        for name, index, value in changes:
            variables[name][index] = value
    return centres


def measure(tmp_path, *, changes=(), edges=None):
    initial, final = tmp_path / "initial.h5", tmp_path / "final.h5"
    write_snapshot(initial, edges=edges)
    write_snapshot(final, time=100., edges=edges, changes=changes)
    with h5py.File(initial) as base, h5py.File(final) as end:
        shape = base["Timestep_0/vars/rho"].shape
        grid = audit.read_grid(base, shape)
        results = audit.measure_snapshot(current=end["Timestep_0/vars"], baseline=base["Timestep_0/vars"],
                                        grid=grid, environment=Potential(), boundary_layers=[1, 2])
    return results, grid


def test_constant_atmosphere_preserves_mass_energy_and_local_fields(tmp_path):
    results, grid = measure(tmp_path)
    whole = results["whole_grid"]
    expected_volume = (grid.x_edges[-1] - grid.x_edges[0]) ** 3
    assert whole["volume_kpc3"] == pytest.approx(expected_volume)
    assert whole["initial"]["mass_g"] == pytest.approx(2 * expected_volume * audit.UNIT_DENSITY_CGS * audit.UNIT_LENGTH_CM**3)
    for total in results.values():
        assert all(value == 0 for value in total["delta"].values())
        if total["cell_count"]:
            assert total["rho"]["min_fractional_change"] == 0
            assert total["prs"]["max_fractional_change"] == 0
            assert total["extrema"]["maximum_speed"]["speed_km_s"] == 0
            assert total["extrema"]["maximum_mach"]["mach"] == 0


def test_signed_changes_use_exact_nonuniform_volumes_and_full_cell_radial_membership(tmp_path):
    index = (3, 3, 3)
    results, grid = measure(tmp_path, changes=[("rho", index, 1.), ("prs", index, 3.)])
    volume = grid.dx[3] * grid.dy[3] * grid.dz[3]
    potential = np.linalg.norm([grid.x[3], grid.y[3], grid.z[3]]) * 1e13
    expected_mass = -volume * audit.UNIT_DENSITY_CGS * audit.UNIT_LENGTH_CM**3
    expected_thermal = volume * audit.UNIT_ENERGY_ERG / (audit.GAMMA_GAS - 1)
    for region in ("whole_grid", "r_lt_30_kpc", "r_lt_80_kpc", "r_lt_100_kpc"):
        assert results[region]["delta"]["mass_g"] == pytest.approx(expected_mass)
        assert results[region]["delta"]["thermal_erg"] == pytest.approx(expected_thermal)
        assert results[region]["delta"]["gravitational_erg"] == pytest.approx(expected_mass * potential)
        assert results[region]["rho"]["min_fractional_change"] == -0.5
        assert results[region]["prs"]["max_fractional_change"] == 0.5
    assert results["r_lt_10_kpc"]["delta"]["mass_g"] == 0
    assert results["r_gt_100_kpc"]["delta"]["mass_g"] == 0
    assert results["boundary_layer_1"]["delta"]["mass_g"] == 0
    assert results["whole_grid"]["rho"]["fractional_volume_sum"] == pytest.approx(-0.5 * volume)


def test_true_3d_speed_and_mach_have_independent_locations_and_boundary_distance(tmp_path):
    corner, inside = (0, 0, 0), (3, 3, 3)
    results, grid = measure(tmp_path, changes=[("vx1", corner, 3e-5), ("vx2", corner, 4e-5),
                                             ("vx3", inside, 2e-5), ("prs", inside, 0.02)])
    speed = results["whole_grid"]["extrema"]["maximum_speed"]
    mach = results["whole_grid"]["extrema"]["maximum_mach"]
    assert (speed["iz"], speed["iy"], speed["ix"]) == corner
    assert speed["speed_km_s"] == pytest.approx(5e-5 * audit.UNIT_VELOCITY_CMS / 1e5)
    assert speed["boundary_distance_kpc"] == pytest.approx(25.)
    assert speed["radial_velocity_km_s"] < 0
    assert (mach["iz"], mach["iy"], mach["ix"]) == inside
    assert mach["mach"] == pytest.approx(2e-5 / np.sqrt((5 / 3) * 0.02 / 2))
    assert results["r_gt_100_kpc"]["extrema"]["maximum_speed"] == speed
    assert results["boundary_layer_1"]["cell_count"] == 6**3 - 4**3
    assert results["boundary_layer_1"]["delta"]["thermal_erg"] == 0
    assert results["boundary_layer_1"]["delta"]["kinetic_erg"] > 0


def inputs(tmp_path):
    root = tmp_path / "test" / "123.kunanyi-ohpc" / "problem"
    root.mkdir(parents=True)
    edges = np.linspace(-150., 150., 7)
    write_snapshot(root / "data.0000.dbl.h5", edges=edges)
    write_snapshot(root / "data.0001.dbl.h5", time=306.6013937879523,
                   edges=edges, changes=[("rho", (3, 3, 3), 1.9)])
    ini = root / "pluto.ini"
    ini.write_text("""[Grid]
X1-grid 1 -150 6 u 150
X2-grid 1 -150 6 u 150
X3-grid 1 -150 6 u 150
[Time]
CFL 0.33
CFL_max_var 1.1
tstop 306.6013937879523
[Solver]
Solver hllc
[Boundary]
X1-beg reflective
X1-end reflective
X2-beg reflective
X2-end reflective
X3-beg reflective
X3-end reflective
[Parameters]
JET_START_TIME 0.0
JET_END_TIME 0.0
JET_ACTIVE_TIME 0.0
JET_PWR 1e45
JET_SPD 0.1
JET_CHI 1.0
JET_EPISODES 1.0
JET_INJECTION_HEIGHT 0.75
JET_INITIAL_RADIUS 0.1
JET_OA_PRIMARY 15.0
JET_OA_SECONDARY 15.0
JET_ROTATION_ANGLE 0.0
JET_X1O 0.0
JET_X2O 0.0
JET_X3O 0.0
ENV_X1O 0.0
ENV_X2O 0.0
ENV_X3O 0.0
STELLAR_MASS 0.0
""")
    environment = root / "environment.csv"
    np.savetxt(environment, [[0, 1e-27, 1e-12, 0, 1e-8, 1e-8],
                            [1000 * audit.UNIT_LENGTH_CM, 1e-27, 1e-12, 0, 1e-8, 1e-8]])
    environment_ini = root / "environment.ini"
    environment_ini.write_text("[Tabulated Environment]\nTabulatedData ./environment.csv\n")
    definitions, definitions_user = root / "definitions.h", root / "definitions_usr.h"
    for path, values in ((definitions, audit.CORE_DEFINES), (definitions_user, audit.USER_DEFINES)):
        path.write_text("".join(f"#define {name} {value}\n" for name, value in values.items()))
    output_index = root / "dbl.h5.out"
    output_index.write_text("0 0.000000e+00 1 0 single_file little rho vx1 vx2 vx3 prs tr1\n"
                           "1 3.066013937879523e+02 1 1 single_file little rho vx1 vx2 vx3 prs tr1\n")
    contract = audit.AuditContract("test", "123.kunanyi-ohpc", "environment.csv", audit.sha256_file(environment),
                                   (6, 6, 6), (150., 150., 150.), (0, 1), 1.)
    return {"case": "test", "job_id": "123.kunanyi-ohpc", "contract": contract,
            "control_root": root, "data_dir": root,
            "environment_path": environment, "pluto_ini": ini,
            "environment_ini": environment_ini, "definitions": definitions, "definitions_user": definitions_user,
            "output_index_file": output_index,
            "output_dir": tmp_path / "audit", "boundary_layers": [1, 2]}


def test_end_to_end_records_provenance_null_initial_kinetic_ratio_and_unmeasured_flux(tmp_path):
    kwargs = inputs(tmp_path)
    metadata = audit.run_audit(**kwargs)
    assert metadata["configuration"]["Boundary"]["X1-beg"] == "reflective"
    assert metadata["snapshot_count"] == 2
    assert metadata["last_age_myr"] == pytest.approx(1.)
    assert all(row["sha256"] is None for row in metadata["snapshot_files"])
    assert all(len(row["sha256"]) == 64 for row in metadata["configuration_files"])
    assert "unmeasured" in metadata["limitations"][0]
    with (kwargs["output_dir"] / "energy_mass_budgets.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    changed = next(row for row in rows if row["snapshot_index"] == "1" and row["region"] == "whole_grid")
    assert float(changed["delta_mass_g"]) < 0
    assert changed["delta_kinetic_erg_over_initial"] == ""
    assert float(changed["delta_total_energy_erg_over_low_power_comparison"]) < 0
    manifest = json.loads((kwargs["output_dir"] / "output_manifest.json").read_text())
    for name, digest in manifest.items():
        assert audit.sha256_file(kwargs["output_dir"] / name) == digest
    with pytest.raises(ValueError, match="overwrite"):
        audit.run_audit(**kwargs)


def test_rejects_changed_geometry_and_nonfinite_primitive(tmp_path):
    kwargs = inputs(tmp_path)
    final = kwargs["data_dir"] / "data.0001.dbl.h5"
    write_snapshot(final, time=audit.CODE_TIME_PER_MYR, edges=np.array([-151., -100., -50., 0., 50., 100., 150.]))
    with pytest.raises(ValueError, match="grid changed"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()
    write_snapshot(final, time=audit.CODE_TIME_PER_MYR, edges=np.linspace(-150., 150., 7), changes=[("vx2", (1, 2, 3), np.nan)])
    with pytest.raises(ValueError, match="non-finite"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_input_mutation_during_streaming_fails_without_publishing(tmp_path, monkeypatch):
    kwargs = inputs(tmp_path)
    original = audit.measure_snapshot

    def mutate(**options):
        result = original(**options)
        kwargs["pluto_ini"].write_text(kwargs["pluto_ini"].read_text() + "\n# changed\n")
        return result

    monkeypatch.setattr(audit, "measure_snapshot", mutate)
    with pytest.raises(ValueError, match="changed during audit"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_snapshot_times_and_negative_density_fail_closed(tmp_path):
    kwargs = inputs(tmp_path)
    final = kwargs["data_dir"] / "data.0001.dbl.h5"
    write_snapshot(final)
    with pytest.raises(ValueError, match="unique"):
        audit.run_audit(**kwargs)
    write_snapshot(final, time=audit.CODE_TIME_PER_MYR, edges=np.linspace(-150., 150., 7), changes=[("rho", (1, 2, 3), -1.)])
    with pytest.raises(ValueError, match="non-positive"):
        audit.run_audit(**kwargs)


@pytest.mark.parametrize("key,old,new,pattern", [
    ("pluto_ini", "X3-end reflective", "X3-end outflow", "six reflective"),
    ("pluto_ini", "JET_ACTIVE_TIME 0.0", "JET_ACTIVE_TIME 1.0", "parameter mismatch"),
    ("pluto_ini", "JET_START_TIME 0.0", "JET_START_TIME 2.0", "parameter mismatch"),
    ("environment_ini", "./environment.csv", "./another.csv", "TabulatedData"),
    ("definitions", "MU_NORM 0.60364", "MU_NORM 0.6", "definition mismatch"),
    ("definitions", "COOLING NO", "COOLING YES", "definition mismatch"),
    ("definitions_user", "DENSITY_JET_POWER", "DENSITY_LENGTH_SCALE", "definition mismatch"),
])
def test_configuration_mismatch_fails_before_science_read(tmp_path, monkeypatch, key, old, new, pattern):
    kwargs = inputs(tmp_path)
    kwargs[key].write_text(kwargs[key].read_text().replace(old, new))
    monkeypatch.setattr(audit, "inspect_file", lambda *a, **k: pytest.fail("configuration must fail before HDF5 inspection"))
    with pytest.raises(ValueError, match=pattern):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_wrong_case_job_and_atmosphere_hash_are_rejected(tmp_path):
    kwargs = inputs(tmp_path)
    with pytest.raises(ValueError, match="case/job identity"):
        audit.run_audit(**{**kwargs, "job_id": "wrong"})
    with pytest.raises(ValueError, match="case/job identity"):
        audit.run_audit(**{**kwargs, "case": "other"})
    kwargs["environment_path"].write_text(kwargs["environment_path"].read_text().replace("1.000000000000000038e-27", "2.000000000000000076e-27") + "\n")
    with pytest.raises(ValueError, match="filename/hash"):
        audit.run_audit(**kwargs)


def test_missing_snapshot_mismatched_index_time_and_short_endpoint_are_rejected(tmp_path):
    from dataclasses import replace
    kwargs = inputs(tmp_path)
    final = kwargs["data_dir"] / "data.0001.dbl.h5"
    with pytest.raises(ValueError, match="indices"):
        audit.run_audit(**{**kwargs, "contract": replace(kwargs["contract"], output_indices=(0, 1, 2))})
    with h5py.File(final, "r+") as h5:
        h5["Timestep_0"].attrs["Time"] = 0.9 * audit.CODE_TIME_PER_MYR
    with pytest.raises(ValueError, match="time disagrees"):
        audit.run_audit(**kwargs)
    kwargs["output_index_file"].write_text("0 0 1 0 single_file little rho vx1 vx2 vx3 prs tr1\n"
        f"1 {0.9 * audit.CODE_TIME_PER_MYR:.15e} 1 1 single_file little rho vx1 vx2 vx3 prs tr1\n")
    with pytest.raises(ValueError, match="does not reach"):
        audit.run_audit(**kwargs)
    final.unlink()
    with pytest.raises(ValueError, match="at least one later"):
        audit.run_audit(**kwargs)


def test_nonzero_tracer_is_not_published_as_a_nojet_control(tmp_path):
    kwargs = inputs(tmp_path)
    with h5py.File(kwargs["data_dir"] / "data.0001.dbl.h5", "r+") as h5:
        h5["Timestep_0/vars/tr1"][1, 2, 3] = 1e-9
    with pytest.raises(ValueError, match="nonzero tracer"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_same_size_rewrite_restoring_mtime_is_detected_by_ctime(tmp_path, monkeypatch):
    import os
    kwargs = inputs(tmp_path)
    original = audit.measure_snapshot
    before = kwargs["pluto_ini"].stat()

    def mutate(**options):
        result = original(**options)
        path = kwargs["pluto_ini"]
        path.write_text(path.read_text().replace("JET_PWR 1e45", "JET_PWR 2e45"))
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        return result

    monkeypatch.setattr(audit, "measure_snapshot", mutate)
    with pytest.raises(ValueError, match="changed during audit"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_hdf5_identity_is_captured_before_inspection(tmp_path, monkeypatch):
    kwargs = inputs(tmp_path)
    original = audit.inspect_file

    def mutate(path, **options):
        result = original(path, **options)
        with h5py.File(path, "r+") as h5:
            h5["Timestep_0/vars/prs"][0, 0, 0] = 3.
        return result

    monkeypatch.setattr(audit, "inspect_file", mutate)
    with pytest.raises(ValueError, match="changed during audit"):
        audit.run_audit(**kwargs)
    assert not kwargs["output_dir"].exists()


def test_six_outputs_accept_actual_index_file_rounding_but_not_an_extra_output(tmp_path):
    from dataclasses import replace
    kwargs = inputs(tmp_path)
    times = [0., 3060.755123, 6075.075123, 9089.351123, 12234.640123, 50. * audit.CODE_TIME_PER_MYR]
    kwargs["contract"] = replace(kwargs["contract"], output_indices=tuple(range(6)), final_age_myr=50.)
    kwargs["pluto_ini"].write_text(kwargs["pluto_ini"].read_text().replace("tstop 306.6013937879523", "tstop 15330.06968940"))
    lines = []
    for index, time in enumerate(times):
        write_snapshot(kwargs["data_dir"] / f"data.{index:04d}.dbl.h5", time=time, edges=np.linspace(-150., 150., 7))
        lines.append(f"{index} {time:.6e} 1 {index} single_file little rho vx1 vx2 vx3 prs tr1\n")
    kwargs["output_index_file"].write_text("".join(lines))
    assert audit.run_audit(**kwargs)["last_age_myr"] == pytest.approx(50.)
    write_snapshot(kwargs["data_dir"] / "data.0006.dbl.h5", time=51. * audit.CODE_TIME_PER_MYR, edges=np.linspace(-150., 150., 7))
    with pytest.raises(ValueError, match="indices"):
        audit.run_audit(**{**kwargs, "output_dir": tmp_path / "extra-output"})


def test_motion_slice_preserves_zx_order_maximum_location_and_signed_changes(tmp_path):
    initial, final = tmp_path / "initial.h5", tmp_path / "final.h5"
    index = (4, 2, 1)
    write_snapshot(initial)
    write_snapshot(final, time=100., changes=[("vx1", index, 3e-5), ("vx3", index, -4e-5),
                                             ("rho", index, 1.), ("prs", index, 3.)])
    with h5py.File(initial) as base, h5py.File(final) as end:
        grid = audit.read_grid(base, (6, 6, 6))
        total = audit.measure_snapshot(current=end["Timestep_0/vars"], baseline=base["Timestep_0/vars"],
                                      grid=grid, environment=Potential(), boundary_layers=[1])
        payload = audit.extract_motion_slice(current=end["Timestep_0/vars"], baseline=base["Timestep_0/vars"],
            grid=grid, maximum=total["whole_grid"]["extrema"]["maximum_speed"], age_myr=100/audit.CODE_TIME_PER_MYR)
    assert payload["array_axis_order"] == "z,x"
    assert payload["selected_y_index"] == index[1]
    assert tuple(payload["maximum_indices_zyx"]) == index
    assert np.array_equal(payload["x_kpc"], grid.x)
    assert np.array_equal(payload["z_kpc"], grid.z)
    assert payload["y_kpc"] == grid.y[index[1]]
    assert payload["current_rho_code"].shape == (6, 6)
    assert payload["rho_fractional_change"][index[0], index[2]] == -.5
    assert payload["prs_fractional_change"][index[0], index[2]] == .5
    assert np.argmax(payload["speed_km_s"]) == np.ravel_multi_index((index[0], index[2]), (6, 6))
    assert payload["speed_km_s"][index[0], index[2]] == pytest.approx(5e-5*audit.UNIT_VELOCITY_CMS/1e5)
    assert payload["current_vx3_code"][index[0], index[2]] == -4e-5
