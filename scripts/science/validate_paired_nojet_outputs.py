#!/usr/bin/env python3
"""Validate new paired boundary controls and bind immutable run receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from measure_q031_fluxes import read_grid
from select_common_age_hdf5 import CODE_TIME_PER_MYR, inspect_file
from snapshot_energy import load_environment


GAMMA_GAS = 5.0 / 3.0
CONST_AMU = 1.66053886e-24
MU_NORM = 0.60364
CONST_PC = 3.0856775807e18
UNIT_DENSITY_CGS = CONST_AMU * MU_NORM
UNIT_LENGTH_CM = CONST_PC * 1e3
UNIT_VELOCITY_CMS = 2.99792458e10
UNIT_PRESSURE_CGS = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS**2
UNIT_ENERGY_ERG = UNIT_PRESSURE_CGS * UNIT_LENGTH_CM**3


FIELDS = ("rho", "prs", "vx1", "vx2", "vx3", "tr1")
FILE_PATTERN = re.compile(r"data\.(\d+)\.dbl\.h5")
FACES = tuple(f"X{axis}-{side}" for axis in (1, 2, 3) for side in ("beg", "end"))
CASE_TABLES = {
    "cluster_002003": ("tabulated_cosmo_002003.csv", "30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa"),
    "group_002031": ("tabulated_cosmo_002031.csv", "1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a"),
}


@dataclass(frozen=True)
class ValidationSpec:
    case: str
    table_name: str
    table_sha256: str
    shape: tuple[int, int, int] = (500, 400, 400)


def _stat(path: Path) -> dict[str, Any]:
    value = path.stat()
    return {"path": str(path.absolute()), "resolved_path": str(path.resolve()), "size_bytes": value.st_size,
            "mtime_ns": value.st_mtime_ns, "ctime_ns": value.st_ctime_ns,
            "device": value.st_dev, "inode": value.st_ino}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(identities: Sequence[Mapping[str, Any]]) -> None:
    for identity in identities:
        if any(identity[key] != value for key, value in _stat(Path(identity["path"])).items()):
            raise ValueError(f"input mutated during or after validation: {identity['path']}")


def _publish(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _ini(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    section = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if section in result:
                raise ValueError(f"duplicate INI section in {path}: {section}")
            result[section] = {}
            continue
        fields = line.split(None, 1)
        if section is None or len(fields) != 2 or fields[0] in result[section]:
            raise ValueError(f"invalid/duplicate INI key in {path}: {line}")
        result[section][fields[0]] = " ".join(fields[1].split())
    return result


def _definitions(path: Path) -> dict[str, str]:
    text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.DOTALL)
    result = {}
    for line in text.splitlines():
        match = re.match(r"\s*#define\s+(\w+)\s+(.+?)\s*$", line.split("//", 1)[0])
        if match:
            value = re.sub(r"\s+", "", match[2])
            if match[1] in result and result[match[1]] != value:
                raise ValueError(f"conflicting macro in {path}: {match[1]}")
            result[match[1]] = value
    return result


def _configuration(run_dir: Path, spec: ValidationSpec, boundary: str, endpoint_myr: float) -> dict[str, Any]:
    ini = _ini(run_dir / "pluto.ini")
    if ini.get("Boundary") != dict.fromkeys(FACES, boundary):
        raise ValueError("all and only the six configured domain faces must match the requested boundary")
    for axis, cells in enumerate(reversed(spec.shape), 1):
        fields = ini.get("Grid", {}).get(f"X{axis}-grid", "").split()
        if (len(fields) != 5 or fields[0] != "1" or fields[3] != "u" or int(fields[2]) != cells
                or float(fields[1]) != -cells / 2 or float(fields[4]) != cells / 2):
            raise ValueError("control configuration must specify the exact uniform 1-kpc grid")
    for name in ("JET_START_TIME", "JET_END_TIME", "JET_ACTIVE_TIME"):
        if float(ini.get("Parameters", {}).get(name, "nan")) != 0.:
            raise ValueError(f"no-jet time must be zero: {name}")
    stop = float(ini.get("Time", {}).get("tstop", "nan")) / CODE_TIME_PER_MYR
    if not math.isfinite(stop) or abs(stop - endpoint_myr) > 1e-6:
        raise ValueError("configured tstop does not match validation mode")
    for key, wanted in (("output_dir", "./outputs"), ("log_dir", "./outputs/logs")):
        if ini.get("Static Grid Output", {}).get(key) != wanted:
            raise ValueError(f"output path must be the fixed run-relative path: {key}={wanted}")
    core = _definitions(run_dir / "definitions.h")
    expected = {"PHYSICS": "HD", "DIMENSIONS": "3", "GEOMETRY": "CARTESIAN", "BODY_FORCE": "VECTOR",
                "EOS": "IDEAL", "COOLING": "NO", "PARTICLES": "NO", "NTRACER": "1",
                "MU_NORM": "0.60364", "UNIT_DENSITY": "((CONST_amu)*MU_NORM)",
                "UNIT_LENGTH": "((CONST_pc)*1e3)", "UNIT_VELOCITY": "CONST_c"}
    for name, value in expected.items():
        if core.get(name) != value:
            raise ValueError(f"unsupported compiled configuration: {name}={core.get(name)}")
    user = _definitions(run_dir / "definitions_usr.h")
    if user.get("DENSITY_PROFILE") != "ENV_TABULATED":
        raise ValueError("control must use the tabulated atmosphere")
    environment_ini = _ini(run_dir / "environment.ini")
    if environment_ini.get("Tabulated Environment", {}).get("TabulatedData") != f"./{spec.table_name}":
        raise ValueError("environment.ini does not select the case's atmosphere table")
    return {"pluto_ini": ini, "environment_ini": environment_ini,
            "definitions": core, "definitions_user": user}


def _index_rows(path: Path, expected_indices: tuple[int, ...]) -> dict[int, tuple[float, float]]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if (len(fields) != 12 or fields[4:6] != ["single_file", "little"]
                or fields[6:] != ["rho", "vx1", "vx2", "vx3", "prs", "tr1"]):
            raise ValueError("invalid double-output index schema")
        index = int(fields[0])
        if index in result:
            raise ValueError("duplicate output index")
        time = Decimal(fields[1])
        if not time.is_finite():
            raise ValueError("non-finite output index time")
        result[index] = (float(time), .5001 * 10.**time.as_tuple().exponent + 1e-10)
    if tuple(result) != expected_indices:
        raise ValueError("output index file is incomplete or has unexpected outputs")
    return result


def _array_hash(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<f8", order="C").tobytes(order="C")).hexdigest()


def _coordinate_check(h5: h5py.File, grid: Any, shape: tuple[int, int, int]) -> None:
    for group, dimensions, vectors in (
        ("cell_coords", shape, (grid.x, grid.y, grid.z)),
        ("node_coords", tuple(value + 1 for value in shape), (grid.x_edges, grid.y_edges, grid.z_edges)),
    ):
        if group not in h5:
            if group == "node_coords":
                continue
            raise ValueError("missing cell coordinates")
        for axis, expected in zip(("X", "Y", "Z"), vectors):
            data = h5[f"{group}/{axis}"]
            if data.ndim == 1:
                if data.shape != expected.shape or not np.array_equal(data[:], expected):
                    raise ValueError(f"inconsistent {group}/{axis}")
            elif data.ndim == 3 and data.shape == dimensions:
                for iz in range(dimensions[0]):
                    actual = np.asarray(data[iz, :, :])
                    target = expected[None, :] if axis == "X" else expected[:, None] if axis == "Y" else expected[iz]
                    if not np.all(actual == target):
                        raise ValueError(f"non-Cartesian or inconsistent {group}/{axis} at z={iz}")
            else:
                raise ValueError(f"coordinate shape mismatch: {group}/{axis}")


def _scan_snapshot(path: Path, *, output_index: int, spec: ValidationSpec, grid_file: Path,
                   index_time: tuple[float, float], initial: bool, environment: Any) -> dict[str, Any]:
    records = inspect_file(path, output_index=output_index)
    if len(records) != 1:
        raise ValueError("each snapshot must contain exactly one timestep")
    snapshot = records[0]
    if snapshot.shape != spec.shape:
        raise ValueError("snapshot field shape differs from required physical grid")
    if abs(snapshot.time_code - index_time[0]) > index_time[1]:
        raise ValueError("HDF5 time disagrees with the saved output index")
    with h5py.File(path, "r") as h5:
        variables = h5[f"{snapshot.timestep}/vars"]
        if set(variables) != set(FIELDS):
            raise ValueError("native field set differs from the six-field no-jet contract")
        grid = read_grid(h5, spec.shape, grid_file=grid_file)
        for cells, edges in zip(reversed(spec.shape), (grid.x_edges, grid.y_edges, grid.z_edges)):
            if not np.array_equal(edges, np.arange(cells + 1, dtype=float) - cells / 2):
                raise ValueError("saved geometry is not the required exact uniform 1-kpc grid")
        _coordinate_check(h5, grid, spec.shape)
        geometry = {name: _array_hash(getattr(grid, name)) for name in ("x", "y", "z", "x_edges", "y_edges", "z_edges")}
        digests = {name: hashlib.sha256() for name in FIELDS}
        ranges = {name: {"minimum": math.inf, "maximum": -math.inf} for name in FIELDS}
        storage = dict.fromkeys(("mass_g", "thermal_erg", "kinetic_erg", "potential_erg"), 0.)
        for name in FIELDS:
            data = variables[name]
            if data.dtype.kind != "f" or data.dtype.itemsize != 8:
                raise ValueError(f"double snapshot field is not float64: {name}")
        area = grid.dy[:, None] * grid.dx[None, :]
        radius_squared_xy = grid.y[:, None]**2 + grid.x[None, :]**2
        for iz in range(spec.shape[0]):
            state = {name: np.asarray(variables[name][iz, :, :], dtype="<f8", order="C") for name in FIELDS}
            for name, values in state.items():
                if not np.all(np.isfinite(values)):
                    raise ValueError(f"non-finite primitive: {path.name}/{name}/z={iz}")
                if name in ("rho", "prs") and np.any(values <= 0):
                    raise ValueError(f"non-positive {name}: {path.name}")
                if name == "tr1" and np.any(values != 0):
                    raise ValueError(f"nonzero tracer in no-jet run: {path.name}")
                if initial and name in ("vx1", "vx2", "vx3") and np.any(values != 0):
                    raise ValueError(f"initial velocity is not zero: {name}")
                ranges[name]["minimum"] = min(ranges[name]["minimum"], float(np.min(values)))
                ranges[name]["maximum"] = max(ranges[name]["maximum"], float(np.max(values)))
                if initial:
                    digests[name].update(values.tobytes(order="C"))
            radius_cm = np.sqrt(radius_squared_xy + grid.z[iz]**2) * UNIT_LENGTH_CM
            if initial:
                for name, physical, unit in (("rho", environment.density_g_cm3, UNIT_DENSITY_CGS),
                                             ("prs", environment.pressure_dyn_cm2, UNIT_PRESSURE_CGS)):
                    expected = np.interp(radius_cm, environment.radius_cm, physical) / unit
                    if not np.allclose(state[name], expected, rtol=1e-11, atol=0.):
                        raise ValueError(f"initial {name} differs from the selected atmosphere profile at z={iz}")
            volume = area * grid.dz[iz]
            mass = state["rho"] * volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
            potential = environment.potential_at_radius(radius_cm)
            speed_squared = sum(state[name]**2 for name in ("vx1", "vx2", "vx3"))
            storage["mass_g"] += float(np.sum(mass))
            storage["thermal_erg"] += float(np.sum(state["prs"] * volume)) * UNIT_ENERGY_ERG / (GAMMA_GAS - 1.)
            storage["kinetic_erg"] += .5 * float(np.sum(state["rho"] * speed_squared * volume)) * UNIT_ENERGY_ERG
            storage["potential_erg"] += float(np.sum(mass * potential))
        field_hashes = {name: digest.hexdigest() for name, digest in digests.items()} if initial else {}
    return {"index": output_index, "timestep": snapshot.timestep, "time_code": snapshot.time_code,
            "time_myr": snapshot.actual_time_myr, "shape_nz_ny_nx": list(spec.shape),
            "grid_geometry_hashes": geometry, "initial_field_hashes": field_hashes, "field_ranges_code": ranges,
            "integrated_storage": storage}


def validate_run(*, run_dir: Path, case: str, boundary: str, mode: str, output: Path,
                 spec: ValidationSpec | None = None) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"refusing to overwrite receipt: {output}")
    if case not in CASE_TABLES and spec is None:
        raise ValueError("unknown production control case")
    if spec is None:
        spec = ValidationSpec(case, *CASE_TABLES[case])
    if spec.case != case or boundary not in ("reflective", "outflow") or mode not in ("smoke", "full"):
        raise ValueError("invalid run identity or mode")
    endpoint, expected_indices = (.25, (0, 1)) if mode == "smoke" else (50., tuple(range(6)))
    outputs = run_dir / "outputs"
    snapshot_paths = sorted(path for path in outputs.iterdir() if FILE_PATTERN.fullmatch(path.name))
    if tuple(int(FILE_PATTERN.fullmatch(path.name)[1]) for path in snapshot_paths) != expected_indices:
        raise ValueError("snapshot inventory is incomplete or contains unexpected outputs")
    paths = {name: run_dir / name for name in ("pluto.ini", "environment.ini", "definitions.h", "definitions_usr.h", "pluto", spec.table_name)}
    paths.update({"grid.out": outputs / "grid.out", "dbl.h5.out": outputs / "dbl.h5.out"})
    paths.update({path.name: path for path in snapshot_paths})
    paths.update({f"validator_source:{name}": Path(__file__).with_name(name) for name in
                  ("validate_paired_nojet_outputs.py", "measure_q031_fluxes.py", "select_common_age_hdf5.py",
                   "snapshot_energy.py", "pluto_h5_level3_ambient_extract.py")})
    identities = {name: _stat(path) for name, path in paths.items()}
    snapshot_names = {path.name for path in snapshot_paths}
    for name, path in paths.items():
        if name not in snapshot_names:
            identities[name]["sha256"] = _hash(path)
    configuration = _configuration(run_dir, spec, boundary, endpoint)
    if identities[spec.table_name]["sha256"] != spec.table_sha256:
        raise ValueError("atmosphere table hash differs from the selected case")
    environment = load_environment(run_dir / spec.table_name)
    index = _index_rows(outputs / "dbl.h5.out", expected_indices)
    snapshots = []
    for number, path in zip(expected_indices, snapshot_paths):
        identities[path.name]["sha256"] = _hash(path)
        record = _scan_snapshot(path, output_index=number, spec=spec, grid_file=outputs / "grid.out",
                                index_time=index[number], initial=number == 0, environment=environment)
        if snapshots and (record["time_code"] <= snapshots[-1]["time_code"] or record["grid_geometry_hashes"] != snapshots[0]["grid_geometry_hashes"]):
            raise ValueError("snapshot times do not increase or grid geometry changed")
        snapshots.append(record)
        print(f"validated_snapshot={case}/{boundary}/{mode}/{number}", flush=True)
    if abs(snapshots[0]["time_myr"]) > 1e-6 or abs(snapshots[-1]["time_myr"] - endpoint) > 1e-6:
        raise ValueError("snapshot chain does not span the required zero-to-endpoint interval")
    if sorted(path for path in outputs.iterdir() if FILE_PATTERN.fullmatch(path.name)) != snapshot_paths:
        raise ValueError("snapshot inventory changed during validation")
    _stable(list(identities.values()))
    receipt = {"schema_version": 1, "status": "validated_paired_control_run", "case": case,
               "boundary": boundary, "mode": mode, "run_dir": str(run_dir.absolute()),
               "configuration": configuration, "input_files": identities, "snapshots": snapshots,
               "grid_geometry_hashes": snapshots[0]["grid_geometry_hashes"],
               "initial_field_hashes": snapshots[0]["initial_field_hashes"],
               "initial_field_hash_encoding": "uncompressed little-endian float64 bytes in z,y,x C order",
               "integrated_storage_definition": "all physical cells, exact FV volumes; thermal=p/(gamma-1), kinetic=rho*v^2/2, potential=rho*Phi_0 with fixed centre-zero tabulated gravity integral",
               "storage_units": {"density_g_cm3": UNIT_DENSITY_CGS, "length_cm": UNIT_LENGTH_CM,
                                 "velocity_cm_s": UNIT_VELOCITY_CMS, "gamma": GAMMA_GAS,
                                 "atomic_mass_unit_g": CONST_AMU, "mean_molecular_weight": MU_NORM,
                                 "parsec_cm": CONST_PC, "pressure_dyn_cm2": UNIT_PRESSURE_CGS,
                                 "energy_erg": UNIT_ENERGY_ERG, "source": "pinned compiled PLUTO constants"},
               "grid_hash_scope": "canonical axes/edges; raw grid.out hash retained separately because its generation timestamp differs",
               "invariants": ["all physical primitive cells finite; rho/prs positive; tracer zero at every saved output",
                              "initial three-component velocity exactly zero",
                              "initial rho/prs match cell-centre radial linear interpolation of the selected table, rtol=1e-11", "all saved grids have the required shape/coordinates"],
               "limitations": ["does not establish energy conservation or validate diagnostic CSV budgets",
                               "saved config hashes do not prove compilation provenance; paired binary equality is checked separately"]}
    _publish(output, receipt)
    return receipt


def validate_pair(receipt_paths: Sequence[Path], output: Path) -> dict[str, Any]:
    if len(receipt_paths) != 2 or output.exists():
        raise ValueError("pair validation needs exactly two receipts and a new output path")
    identities = [{**_stat(path), "sha256": _hash(path)} for path in receipt_paths]
    receipts = [json.loads(path.read_text()) for path in receipt_paths]
    if any(row.get("schema_version") != 1 or row.get("status") != "validated_paired_control_run" for row in receipts):
        raise ValueError("pair requires two successful run-validation receipts")
    a, b = receipts
    if a["case"] != b["case"] or a["mode"] != b["mode"] or {a["boundary"], b["boundary"]} != {"reflective", "outflow"}:
        raise ValueError("paired case/mode or complementary boundary identities differ")
    if a["run_dir"] == b["run_dir"]:
        raise ValueError("pair must identify two distinct run directories")
    for row in receipts:
        _stable(list(row["input_files"].values()))
    for key in ("grid_geometry_hashes", "initial_field_hashes"):
        if a[key] != b[key]:
            raise ValueError(f"pair mismatch: {key}")
    for name in ("pluto", "definitions.h", "definitions_usr.h"):
        if a["input_files"][name]["sha256"] != b["input_files"][name]["sha256"]:
            raise ValueError(f"pair mismatch: {name} hash")
    for key in ("environment_ini", "definitions", "definitions_user"):
        if a["configuration"][key] != b["configuration"][key]:
            raise ValueError(f"pair configuration mismatch: {key}")
    for row in receipts:
        table_name = Path(row["configuration"]["environment_ini"]["Tabulated Environment"]["TabulatedData"]).name
        row["paired_table_sha256"] = row["input_files"][table_name]["sha256"]
    if a["paired_table_sha256"] != b["paired_table_sha256"]:
        raise ValueError("pair atmosphere table hashes differ")
    for row in receipts:
        if row["configuration"]["pluto_ini"]["Boundary"] != dict.fromkeys(FACES, row["boundary"]):
            raise ValueError("receipt boundary settings disagree with its identity")
    left = {key: value for key, value in a["configuration"]["pluto_ini"].items() if key != "Boundary"}
    right = {key: value for key, value in b["configuration"]["pluto_ini"].items() if key != "Boundary"}
    if left != right:
        raise ValueError("paired pluto.ini differs outside the six boundary settings")
    _stable([*identities, *(item for row in receipts for item in row["input_files"].values())])
    receipt = {"schema_version": 1, "status": "validated_paired_control_identity", "case": a["case"], "mode": a["mode"],
               "source_receipts": identities, "binary_sha256": a["input_files"]["pluto"]["sha256"],
               "atmosphere_sha256": a["paired_table_sha256"], "grid_geometry_hashes": a["grid_geometry_hashes"],
               "initial_field_hashes": a["initial_field_hashes"],
               "only_semantic_configuration_differences": [f"Boundary/{face}" for face in FACES],
               "diagnostic_budget_status": "not_checked_by_this_identity_validator"}
    _publish(output, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--case", choices=tuple(CASE_TABLES))
    parser.add_argument("--boundary", choices=("reflective", "outflow"))
    parser.add_argument("--mode", choices=("smoke", "full"))
    parser.add_argument("--pair-receipts", type=Path, nargs=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_arguments = (args.run_dir, args.case, args.boundary, args.mode)
    if args.pair_receipts:
        if any(value is not None for value in run_arguments):
            parser.error("pair mode cannot include run arguments")
        validate_pair(args.pair_receipts, args.output)
    else:
        if any(value is None for value in run_arguments):
            parser.error("run mode requires --run-dir, --case, --boundary and --mode")
        validate_run(run_dir=args.run_dir, case=args.case, boundary=args.boundary, mode=args.mode, output=args.output)


if __name__ == "__main__":
    main()
