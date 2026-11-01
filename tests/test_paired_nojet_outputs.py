from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCIENCE = Path(__file__).resolve().parents[1] / "scripts" / "science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
import validate_paired_nojet_outputs as validator


def make_run(tmp_path, boundary="reflective", mode="smoke", *, perturb_initial=False):
    root = tmp_path / f"test_{boundary}"
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    table = root / "environment.csv"
    table.write_text("".join(f"{r} {2 * validator.UNIT_DENSITY_CGS:.17g} {2 * validator.UNIT_PRESSURE_CGS:.17g} 0 1e-8 1e-8\n" for r in (0., 1e25)))
    (root / "environment.ini").write_text("[Tabulated Environment]\nTabulatedData ./environment.csv\n")
    endpoint = .25 if mode == "smoke" else 50.
    (root / "pluto.ini").write_text(
        "[Grid]\nX1-grid 1 -2 4 u 2\nX2-grid 1 -2 4 u 2\nX3-grid 1 -2 4 u 2\n"
        f"[Time]\ntstop {endpoint * validator.CODE_TIME_PER_MYR:.15e}\nCFL 0.33\n"
        "[Static Grid Output]\noutput_dir ./outputs\nlog_dir ./outputs/logs\n"
        "[Boundary]\n" + "".join(f"{face} {boundary}\n" for face in validator.FACES) +
        "[Parameters]\nJET_START_TIME 0\nJET_END_TIME 0\nJET_ACTIVE_TIME 0\n")
    (root / "definitions.h").write_text("""#define PHYSICS HD
#define DIMENSIONS 3
#define GEOMETRY CARTESIAN
#define BODY_FORCE VECTOR
#define EOS IDEAL
#define COOLING NO
#define PARTICLES NO
#define NTRACER 1
#define MU_NORM 0.60364
#define UNIT_DENSITY ((CONST_amu)*MU_NORM)
#define UNIT_LENGTH ((CONST_pc)*1e3)
#define UNIT_VELOCITY CONST_c
""")
    (root / "definitions_usr.h").write_text("#define DENSITY_PROFILE ENV_TABULATED\n")
    (root / "pluto").write_bytes(b"same synthetic executable")
    edges = np.arange(5.) - 2.
    centers = (edges[:-1] + edges[1:]) / 2
    grid_text = f"# Generated separately: {boundary}\n"
    for _ in range(3):
        grid_text += "4\n" + "".join(f"{index+1} {left} {right}\n" for index, (left, right) in enumerate(zip(edges[:-1], edges[1:])))
    (outputs / "grid.out").write_text(grid_text)
    times = [0., .25] if mode == "smoke" else [0., 10., 20., 30., 40., 50.]
    index_text = ""
    for index, age in enumerate(times):
        index_text += f"{index} {age * validator.CODE_TIME_PER_MYR:.6e} 1 {index} single_file little rho vx1 vx2 vx3 prs tr1\n"
        with h5py.File(outputs / f"data.{index:04d}.dbl.h5", "w") as h5:
            for axis, centre in (("X", centers[None, None, :]), ("Y", centers[None, :, None]), ("Z", centers[:, None, None])):
                h5.create_dataset(f"cell_coords/{axis}", data=np.broadcast_to(centre, (4, 4, 4)))
            for axis in ("X", "Y", "Z"):
                h5.create_dataset(f"node_coords/{axis}", data=edges)
            step = h5.create_group(f"Timestep_{index}")
            step.attrs["Time"] = age * validator.CODE_TIME_PER_MYR
            fields = step.create_group("vars")
            for name in validator.FIELDS:
                value = 2. if name in ("rho", "prs") else 0.
                fields.create_dataset(name, data=np.full((4, 4, 4), value, dtype=np.float64))
            if index == 0 and perturb_initial:
                fields["rho"][1, 2, 3] = 2.01
            if index > 0:
                fields["vx1"][0, 1, 2] = -1e-5
    (outputs / "dbl.h5.out").write_text(index_text)
    spec = validator.ValidationSpec("test", table.name, hashlib.sha256(table.read_bytes()).hexdigest(), (4, 4, 4))
    return {"run_dir": root, "case": "test", "boundary": boundary, "mode": mode,
            "output": tmp_path / f"{boundary}_{mode}.json", "spec": spec}


def alter_field(options, index, field, value):
    with h5py.File(options["run_dir"] / "outputs" / f"data.{index:04d}.dbl.h5", "r+") as h5:
        h5[f"Timestep_{index}/vars/{field}"][1, 2, 3] = value


def test_run_receipt_hashes_all_hdf5_and_initial_field_bytes(tmp_path):
    options = make_run(tmp_path)
    receipt = validator.validate_run(**options)
    assert receipt["status"] == "validated_paired_control_run"
    assert receipt["snapshots"][-1]["time_myr"] == .25
    expected = hashlib.sha256(np.full((4, 4, 4), 2., dtype="<f8").tobytes()).hexdigest()
    assert receipt["initial_field_hashes"]["rho"] == expected
    for index in (0, 1):
        name = f"data.{index:04d}.dbl.h5"
        assert receipt["input_files"][name]["sha256"] == hashlib.sha256((options["run_dir"] / "outputs" / name).read_bytes()).hexdigest()
    saved = options["output"].read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        validator.validate_run(**options)
    assert options["output"].read_bytes() == saved
    assert not list(tmp_path.glob(".reflective_smoke.json.*"))


def test_independent_native_storage_has_correct_mass_thermal_kinetic_and_potential_units(tmp_path):
    options = make_run(tmp_path)
    with h5py.File(options["run_dir"] / "outputs/data.0001.dbl.h5", "r+") as h5:
        for name, value in (("vx1", 3e-5), ("vx2", 4e-5), ("vx3", 0.)):
            h5[f"Timestep_1/vars/{name}"][:] = value
    receipt = validator.validate_run(**options)
    initial = receipt["snapshots"][0]["integrated_storage"]
    current = receipt["snapshots"][1]["integrated_storage"]
    mass_per_cell = 2. * validator.UNIT_DENSITY_CGS * validator.UNIT_LENGTH_CM**3
    centres = np.arange(4.) - 1.5
    zz, yy, xx = np.meshgrid(centres, centres, centres, indexing="ij")
    expected_phi = np.sqrt(xx**2 + yy**2 + zz**2) * validator.UNIT_LENGTH_CM * 1e-8
    assert current["mass_g"] == pytest.approx(64 * mass_per_cell)
    assert current["thermal_erg"] == pytest.approx(64 * 2. * validator.UNIT_ENERGY_ERG / (5./3. - 1.))
    assert current["kinetic_erg"] == pytest.approx(64 * .5 * 2. * (3e-5**2 + 4e-5**2) * validator.UNIT_ENERGY_ERG)
    assert current["potential_erg"] == pytest.approx(mass_per_cell * np.sum(expected_phi))
    assert initial["kinetic_erg"] == 0.
    for name in ("mass_g", "thermal_erg", "potential_erg"):
        assert current[name] == initial[name]


def test_pair_requires_same_physics_but_accepts_grid_file_generation_timestamp_difference(tmp_path):
    left, right = make_run(tmp_path, "reflective"), make_run(tmp_path, "outflow")
    a, b = validator.validate_run(**left), validator.validate_run(**right)
    assert a["input_files"]["grid.out"]["sha256"] != b["input_files"]["grid.out"]["sha256"]
    pair = validator.validate_pair([left["output"], right["output"]], tmp_path / "pair.json")
    assert pair["status"] == "validated_paired_control_identity"
    assert pair["only_semantic_configuration_differences"] == [f"Boundary/{face}" for face in validator.FACES]


@pytest.mark.parametrize("index,field,value,error", [(1, "tr1", 1e-20, "nonzero tracer"),
    (0, "vx2", 1e-20, "initial velocity"), (1, "rho", 0., "non-positive"),
    (1, "prs", -1., "non-positive"), (1, "vx3", np.inf, "non-finite"),
    (0, "prs", np.nan, "non-finite")])
def test_bad_native_fields_fail_without_receipt(tmp_path, index, field, value, error):
    options = make_run(tmp_path)
    alter_field(options, index, field, value)
    with pytest.raises(ValueError, match=error):
        validator.validate_run(**options)
    assert not options["output"].exists()


def test_full_mode_checks_intermediate_snapshots_and_missing_outputs(tmp_path):
    options = make_run(tmp_path, mode="full")
    alter_field(options, 3, "rho", np.nan)
    with pytest.raises(ValueError, match="non-finite"):
        validator.validate_run(**options)
    (options["run_dir"] / "outputs/data.0003.dbl.h5").unlink()
    with pytest.raises(ValueError, match="inventory"):
        validator.validate_run(**options)
    assert not options["output"].exists()


def test_complete_full_run_reaches_exact_endpoint_with_all_six_outputs(tmp_path):
    options = make_run(tmp_path, mode="full")
    receipt = validator.validate_run(**options)
    assert [row["index"] for row in receipt["snapshots"]] == list(range(6))
    assert receipt["snapshots"][-1]["time_myr"] == pytest.approx(50.)
    assert receipt["snapshots"][0]["field_ranges_code"]["vx1"] == {"minimum": 0., "maximum": 0.}


@pytest.mark.parametrize("filename,old,new,error", [
    ("definitions.h", "PARTICLES NO", "PARTICLES YES", "compiled configuration"),
    ("definitions.h", "MU_NORM 0.60364", "MU_NORM 0.6", "compiled configuration"),
    ("pluto.ini", "JET_ACTIVE_TIME 0", "JET_ACTIVE_TIME 1", "no-jet time"),
    ("pluto.ini", "X2-grid 1 -2 4 u 2", "X2-grid 1 -4 4 u 4", "uniform 1-kpc"),
    ("environment.ini", "./environment.csv", "./wrong.csv", "does not select"),
    ("environment.csv", "1e-8", "2e-8", "table hash"),
])
def test_invalid_setup_fails_before_reading_large_snapshot_payloads(tmp_path, monkeypatch, filename, old, new, error):
    options = make_run(tmp_path)
    path = options["run_dir"] / filename
    path.write_text(path.read_text().replace(old, new))
    original = validator._hash

    def compact_only(path):
        if path.name.endswith(".h5"):
            pytest.fail("invalid setup must be rejected before hashing large snapshots")
        return original(path)

    monkeypatch.setattr(validator, "_hash", compact_only)
    with pytest.raises(ValueError, match=error):
        validator.validate_run(**options)


def test_field_coordinate_corruption_outside_extracted_axis_is_detected(tmp_path):
    options = make_run(tmp_path)
    with h5py.File(options["run_dir"] / "outputs/data.0001.dbl.h5", "r+") as h5:
        h5["cell_coords/X"][0, 0, 0] = -1.6
    with pytest.raises(ValueError, match="non-Cartesian"):
        validator.validate_run(**options)


def test_saved_time_and_endpoint_mismatch_are_rejected(tmp_path):
    options = make_run(tmp_path)
    final = options["run_dir"] / "outputs/data.0001.dbl.h5"
    with h5py.File(final, "r+") as h5:
        h5["Timestep_1"].attrs["Time"] = .2 * validator.CODE_TIME_PER_MYR
    with pytest.raises(ValueError, match="time disagrees"):
        validator.validate_run(**options)
    path = options["run_dir"] / "outputs/dbl.h5.out"
    path.write_text("0 0.000000e+00 1 0 single_file little rho vx1 vx2 vx3 prs tr1\n"
                    f"1 {.2*validator.CODE_TIME_PER_MYR:.6e} 1 1 single_file little rho vx1 vx2 vx3 prs tr1\n")
    with pytest.raises(ValueError, match="zero-to-endpoint"):
        validator.validate_run(**options)


@pytest.mark.parametrize("bad_change,error", [("binary", "pluto hash"),
                                               ("cfl", "outside the six")])
def test_pair_rejects_unequal_initial_conditions_binary_or_other_config(tmp_path, bad_change, error):
    left, right = make_run(tmp_path, "reflective"), make_run(tmp_path, "outflow", perturb_initial=bad_change == "initial")
    if bad_change == "binary":
        (right["run_dir"] / "pluto").write_bytes(b"different executable")
    if bad_change == "cfl":
        path = right["run_dir"] / "pluto.ini"
        path.write_text(path.read_text().replace("CFL 0.33", "CFL 0.3"))
    validator.validate_run(**left)
    validator.validate_run(**right)
    with pytest.raises(ValueError, match=error):
        validator.validate_pair([left["output"], right["output"]], tmp_path / "pair.json")
    assert not (tmp_path / "pair.json").exists()


def test_boundary_config_and_output_path_mismatch_fail(tmp_path):
    options = make_run(tmp_path)
    path = options["run_dir"] / "pluto.ini"
    original = path.read_text()
    path.write_text(original.replace("X3-end reflective", "X3-end outflow"))
    with pytest.raises(ValueError, match="six configured"):
        validator.validate_run(**options)
    path.write_text(original.replace("output_dir ./outputs", "output_dir /tmp/elsewhere"))
    with pytest.raises(ValueError, match="output path"):
        validator.validate_run(**options)


def test_mutation_restoring_size_and_mtime_is_caught_by_ctime(tmp_path, monkeypatch):
    options = make_run(tmp_path)
    original = validator._scan_snapshot

    def mutate(path, **kwargs):
        result = original(path, **kwargs)
        metadata = path.stat()
        with h5py.File(path, "r+") as h5:
            h5[f"Timestep_{kwargs['output_index']}/vars/rho"][0, 0, 0] = 2.01
        os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        return result

    monkeypatch.setattr(validator, "_scan_snapshot", mutate)
    with pytest.raises(ValueError, match="mutated"):
        validator.validate_run(**options)
    assert not options["output"].exists()


def test_pair_refuses_stale_run_receipts(tmp_path):
    left, right = make_run(tmp_path, "reflective"), make_run(tmp_path, "outflow")
    validator.validate_run(**left)
    validator.validate_run(**right)
    alter_field(right, 1, "prs", 2.1)
    with pytest.raises(ValueError, match="mutated"):
        validator.validate_pair([left["output"], right["output"]], tmp_path / "pair.json")


def test_atomic_receipt_publication_never_overwrites(tmp_path):
    output = tmp_path / "receipt.json"
    validator._publish(output, {"status": "first"})
    with pytest.raises(FileExistsError):
        validator._publish(output, {"status": "second"})
    assert json.loads(output.read_text()) == {"status": "first"}
    assert not list(tmp_path.glob(".receipt.json.*"))


def test_initial_profile_must_match_table_even_if_twins_share_wrong_values(tmp_path):
    options = make_run(tmp_path, perturb_initial=True)
    with pytest.raises(ValueError, match="initial rho differs from the selected atmosphere"):
        validator.validate_run(**options)
    assert not options["output"].exists()


def test_exact_compiled_units_are_recorded(tmp_path):
    receipt = validator.validate_run(**make_run(tmp_path))
    units = receipt["storage_units"]
    assert units["density_g_cm3"] == 1.66053886e-24 * 0.60364
    assert units["length_cm"] == 3.0856775807e21
    assert units["velocity_cm_s"] == 2.99792458e10


def test_initial_profile_checks_radial_interpolation_in_physical_units(tmp_path):
    options = make_run(tmp_path)
    table = options["run_dir"] / "environment.csv"
    d, p = validator.UNIT_DENSITY_CGS, validator.UNIT_PRESSURE_CGS
    table.write_text(f"0 {2*d:.17g} {2*p:.17g} 0 1e-8 1e-8\n1e25 {3*d:.17g} {4*p:.17g} 0 1e-8 1e-8\n")
    options["spec"] = validator.ValidationSpec("test", table.name, hashlib.sha256(table.read_bytes()).hexdigest(), (4, 4, 4))
    z, y, x = np.meshgrid(*(np.arange(4.) - 1.5 for _ in range(3)), indexing="ij")
    fraction = np.sqrt(x*x + y*y + z*z) * validator.UNIT_LENGTH_CM / 1e25
    with h5py.File(options["run_dir"] / "outputs/data.0000.dbl.h5", "r+") as h5:
        h5["Timestep_0/vars/rho"][:] = 2. + fraction
        h5["Timestep_0/vars/prs"][:] = 2. + 2.*fraction
    assert validator.validate_run(**options)["status"] == "validated_paired_control_run"
