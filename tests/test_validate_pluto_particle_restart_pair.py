from __future__ import annotations

import json
import hashlib
import struct
import subprocess
import sys
from pathlib import Path

import pytest
import h5py
import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "science"
    / "validate_pluto_particle_restart_pair.py"
)
RESTART_RECORD = struct.Struct("<17i4x2d40x")
FLUID_OUTPUT_SLOT = 2
FLOAT_OUTPUT_SLOT = 3
PARTICLE_OUTPUT_SLOT = 8
FLUID_RESTART_INDEX = 2
FLOAT_RESTART_INDEX = 10
PARTICLE_RESTART_INDEX = 1000
FLUID_TIME = 3065.934704693023
PARTICLE_TIME = 3065.934704693
PARTICLE_STEP = 10578
PLUTO_VERSION = "4.4-patch3"
FIELD_NAMES = [
    "id",
    "x1",
    "x2",
    "x3",
    "vx1",
    "vx2",
    "vx3",
    "tinj",
    "color",
    "tracer",
    "last_shock_time",
    "density",
    "pressure",
]
FIELD_DIMS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1]
LIVE_PARTICLE_COUNT = 42_032
LIVE_HEADER_OFFSET = 547
LIVE_PAYLOAD_BYTES = 5_043_840
LIVE_FILE_BYTES = 5_044_387


def pack_restart_record(
    *,
    nstep: int,
    time: float,
    dt: float,
    nfiles: dict[int, int],
) -> bytes:
    output_indices = [-1] * 16
    for slot, index in nfiles.items():
        output_indices[slot] = index
    return RESTART_RECORD.pack(nstep, *output_indices, time, dt)


def write_restart_out(path: Path, records: list[bytes]) -> None:
    path.write_bytes(b"".join(records))


def valid_restart_records() -> list[bytes]:
    return [
        pack_restart_record(
            nstep=1,
            time=0.1,
            dt=0.1,
            nfiles={FLUID_OUTPUT_SLOT: 0, 3: 0, PARTICLE_OUTPUT_SLOT: 0},
        ),
        pack_restart_record(
            nstep=5289,
            time=1532.9673523465115,
            dt=0.2,
            nfiles={FLUID_OUTPUT_SLOT: 1, 3: 5, PARTICLE_OUTPUT_SLOT: 500},
        ),
        pack_restart_record(
            nstep=10578,
            time=FLUID_TIME,
            dt=0.32137,
            nfiles={
                FLUID_OUTPUT_SLOT: FLUID_RESTART_INDEX,
                3: 10,
                PARTICLE_OUTPUT_SLOT: PARTICLE_RESTART_INDEX,
            },
        ),
    ]


def particle_metadata(*, time: float = PARTICLE_TIME) -> dict[str, object]:
    return {
        "PLUTO_version": PLUTO_VERSION,
        "dimensions": 3,
        "nflux": 5,
        "endianity": "little",
        "precision": "double",
        "particletype": 1,
        "nparticles": 2,
        "nfields": len(FIELD_NAMES),
        "nelem": sum(FIELD_DIMS),
        "idCounter": 2,
        "dt_particles": 0.25,
        "time": time,
        "stepNumber": PARTICLE_STEP,
        "field_names": FIELD_NAMES.copy(),
        "field_dim": FIELD_DIMS.copy(),
    }


def valid_particle_rows() -> list[list[float]]:
    return [
        [
            1.0,
            -1.0,
            0.0,
            1.0,
            0.1,
            0.2,
            0.3,
            100.0,
            0.1,
            0.2,
            90.0,
            91.0,
            92.0,
            1.0e-3,
            1.0e-8,
        ],
        [
            2.0,
            2.0,
            -2.0,
            3.0,
            -0.1,
            -0.2,
            -0.3,
            200.0,
            0.3,
            0.4,
            190.0,
            191.0,
            192.0,
            2.0e-3,
            2.0e-8,
        ],
    ]


def write_particle_file(
    path: Path,
    *,
    metadata: dict[str, object] | None = None,
    rows: list[list[float]] | None = None,
    payload_size: int | None = None,
) -> int:
    values = particle_metadata() if metadata is None else metadata
    lines: list[str] = []
    if "PLUTO_version" in values:
        lines.append(
            f"# PLUTO {values['PLUTO_version']} (synthetic) binary particle data file\n"
        )
    for key in (
        "dimensions",
        "nflux",
        "dt_particles",
        "endianity",
        "nparticles",
        "idCounter",
        "particletype",
        "precision",
        "time",
        "stepNumber",
        "nfields",
        "nelem",
        "field_names",
        "field_dim",
    ):
        if key in values:
            value = values[key]
            if isinstance(value, list):
                value = "  ".join(str(item) for item in value)
            lines.append(f"# {key}      {value}\n")
    header = "".join(lines).encode("ascii")
    particle_rows = valid_particle_rows() if rows is None else rows
    payload = b"".join(
        struct.pack(f"<{len(row)}d", *row) for row in particle_rows
    )
    if payload_size is None:
        payload_size = len(payload)
    if payload_size <= len(payload):
        payload = payload[:payload_size]
    else:
        payload += b"\x00" * (payload_size - len(payload))
    path.write_bytes(header + payload)
    return len(header)


def build_valid_pair(
    tmp_path: Path,
    *,
    particle_time: float = PARTICLE_TIME,
    metadata: dict[str, object] | None = None,
    rows: list[list[float]] | None = None,
    payload_size: int | None = None,
) -> tuple[Path, Path, int]:
    restart_out = tmp_path / "restart.out"
    write_restart_out(restart_out, valid_restart_records())
    particle_file = tmp_path / f"particles.{PARTICLE_RESTART_INDEX:04d}.dbl"
    selected_metadata = (
        particle_metadata(time=particle_time) if metadata is None else metadata
    )
    header_offset = write_particle_file(
        particle_file,
        metadata=selected_metadata,
        rows=rows,
        payload_size=payload_size,
    )
    return restart_out, particle_file, header_offset


def run_validator(
    restart_out: Path,
    *,
    fluid_output_slot: int = FLUID_OUTPUT_SLOT,
    particle_output_slot: int = PARTICLE_OUTPUT_SLOT,
    include_expected_schema: bool = True,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--restart-out",
        str(restart_out),
        "--fluid-restart-index",
        str(FLUID_RESTART_INDEX),
        "--fluid-output-slot",
        str(fluid_output_slot),
        "--particle-output-slot",
        str(particle_output_slot),
    ]
    if include_expected_schema:
        command.extend(
            [
                "--expected-field-names",
                *FIELD_NAMES,
                "--expected-field-dims",
                *(str(value) for value in FIELD_DIMS),
                "--expected-step",
                str(PARTICLE_STEP),
            ]
        )
    if extra_args:
        command.extend(extra_args)
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_emits_deterministic_json_for_live_goal038_record(tmp_path: Path) -> None:
    restart_out, particle_file, header_offset = build_valid_pair(tmp_path)

    result = run_validator(restart_out)

    expected = {
        "fluid_restart": {
            "dt": 0.32137,
            "index": FLUID_RESTART_INDEX,
            "nstep": 10578,
            "output_slot": FLUID_OUTPUT_SLOT,
            "record_index": 2,
            "time": FLUID_TIME,
        },
        "particle_restart": {
            "PLUTO_version": PLUTO_VERSION,
            "content": {
                "id_max": 2,
                "id_min": 1,
                "records_scanned": 2,
                "unique_ids": 2,
            },
            "dimensions": 3,
            "dt_particles": 0.25,
            "endianity": "little",
            "field_dim": FIELD_DIMS,
            "field_names": FIELD_NAMES,
            "header_offset": header_offset,
            "idCounter": 2,
            "index": PARTICLE_RESTART_INDEX,
            "nelem": sum(FIELD_DIMS),
            "nfields": len(FIELD_NAMES),
            "nflux": 5,
            "nparticles": 2,
            "output_slot": PARTICLE_OUTPUT_SLOT,
            "path": str(particle_file),
            "particletype": 1,
            "precision": "double",
            "size_bytes": particle_file.stat().st_size,
            "stepNumber": PARTICLE_STEP,
            "time": PARTICLE_TIME,
        },
        "restart_out": str(restart_out),
        "status": "ok",
        "time_atol": 0.005,
        "time_delta": abs(PARTICLE_TIME - FLUID_TIME),
    }
    expected_json = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout == expected_json
    assert run_validator(restart_out).stdout == expected_json


def test_json_output_writes_the_same_report_without_stdout(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    expected = run_validator(restart_out)
    json_output = tmp_path / "pair.json"

    result = run_validator(
        restart_out,
        extra_args=["--json-output", str(json_output)],
    )

    assert expected.returncode == 0, expected.stderr
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""
    assert json_output.read_text() == expected.stdout


def test_live_goal038_size_evidence_matches_the_exact_schema() -> None:
    assert LIVE_PARTICLE_COUNT * sum(FIELD_DIMS) * 8 == LIVE_PAYLOAD_BYTES
    assert LIVE_HEADER_OFFSET + LIVE_PAYLOAD_BYTES == LIVE_FILE_BYTES


def test_rejects_expected_particle_index_mismatch(tmp_path: Path) -> None:
    restart_out = tmp_path / "restart.out"
    write_restart_out(restart_out, valid_restart_records())

    result = run_validator(
        restart_out,
        extra_args=["--expected-particle-index", "999"],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        "error: particle restart index mismatch: output slot 8 contains 1000, "
        "expected 999\n"
    )


def test_rejects_particle_time_outside_default_atol(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(
        tmp_path,
        particle_time=FLUID_TIME + 0.006,
    )

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "particle time mismatch" in result.stderr
    assert "exceeds atol 0.005" in result.stderr


def test_accepts_particle_time_within_configured_atol(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(
        tmp_path,
        particle_time=FLUID_TIME + 0.006,
    )

    result = run_validator(restart_out, extra_args=["--atol", "0.01"])

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["time_atol"] == 0.01
    assert report["time_delta"] == pytest.approx(0.006)


def test_rejects_truncated_particle_payload(tmp_path: Path) -> None:
    expected_payload_size = 2 * sum(FIELD_DIMS) * 8
    restart_out, particle_file, header_offset = build_valid_pair(
        tmp_path,
        payload_size=expected_payload_size - 8,
    )

    result = run_validator(restart_out)

    expected_size = header_offset + expected_payload_size
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: particle file size mismatch for {particle_file}: expected "
        f"{expected_size} bytes from header, found {particle_file.stat().st_size}\n"
    )


def test_rejects_truncated_restart_record(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    restart_out.write_bytes(restart_out.read_bytes() + b"\x00")

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {restart_out}: size 385 is not a multiple of the 128-byte "
        "Restart record size\n"
    )


def test_rejects_ambiguous_fluid_restart_records(tmp_path: Path) -> None:
    restart_out = tmp_path / "restart.out"
    records = valid_restart_records()
    records.append(
        pack_restart_record(
            nstep=10579,
            time=FLUID_TIME + 0.001,
            dt=0.32137,
            nfiles={
                FLUID_OUTPUT_SLOT: FLUID_RESTART_INDEX,
                PARTICLE_OUTPUT_SLOT: PARTICLE_RESTART_INDEX + 1,
            },
        )
    )
    write_restart_out(restart_out, records)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        "error: expected exactly one Restart record with output slot 2 equal "
        "to fluid restart index 2; found 2\n"
    )


def test_rejects_restart_catalogue_with_unexpected_record_count(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    records = valid_restart_records()
    records.append(
        pack_restart_record(
            nstep=12000,
            time=3500.0,
            dt=0.3,
            nfiles={FLUID_OUTPUT_SLOT: 3, FLOAT_OUTPUT_SLOT: 11, PARTICLE_OUTPUT_SLOT: 1100},
        )
    )
    write_restart_out(restart_out, records)

    result = run_validator(
        restart_out,
        extra_args=["--expected-record-count", "3"],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {restart_out}: expected exactly 3 Restart records, found 4\n"
    )


def test_rejects_selected_record_companion_output_index_mismatch(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    records = valid_restart_records()
    records[-1] = pack_restart_record(
        nstep=PARTICLE_STEP,
        time=FLUID_TIME,
        dt=0.32137,
        nfiles={
            FLUID_OUTPUT_SLOT: FLUID_RESTART_INDEX,
            FLOAT_OUTPUT_SLOT: FLOAT_RESTART_INDEX - 1,
            PARTICLE_OUTPUT_SLOT: PARTICLE_RESTART_INDEX,
        },
    )
    write_restart_out(restart_out, records)

    result = run_validator(
        restart_out,
        extra_args=[
            "--expected-output-index",
            str(FLOAT_OUTPUT_SLOT),
            str(FLOAT_RESTART_INDEX),
        ],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        "error: selected Restart record 2: output slot 3 contains 9, expected 10\n"
    )


def test_rejects_particle_step_that_differs_from_selected_restart_record(
    tmp_path: Path,
) -> None:
    metadata = particle_metadata()
    metadata["stepNumber"] = PARTICLE_STEP - 1
    restart_out, particle_file, _ = build_valid_pair(tmp_path, metadata=metadata)

    result = run_validator(restart_out, include_expected_schema=False)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: stepNumber {PARTICLE_STEP - 1} does not match "
        f"selected Restart record nstep {PARTICLE_STEP}\n"
    )


def write_fluid_hdf5(path: Path, *, time: float = FLUID_TIME) -> None:
    shape = (2, 3, 4)
    with h5py.File(path, "w") as h5:
        timestep = h5.create_group("Timestep_2")
        timestep.attrs["Time"] = time
        variables = timestep.create_group("vars")
        for index, name in enumerate(("rho", "prs", "tr1", "vx1", "vx2", "vx3"), 1):
            variables.create_dataset(name, data=np.full(shape, float(index)))


def write_fluid_catalogue(
    path: Path,
    *,
    selected_time: float = FLUID_TIME,
    selected_step: int = PARTICLE_STEP,
) -> None:
    path.write_text(
        "0 0.0 0.1 1 single_file little rho vx1 vx2 vx3 prs tr1\n"
        "1 1532.9673523465115 0.2 5289 single_file little rho vx1 vx2 vx3 prs tr1\n"
        f"2 {selected_time:.17g} 0.32137 {selected_step} "
        "single_file little rho vx1 vx2 vx3 prs tr1\n"
    )


def test_fluid_hdf5_and_all_restart_inputs_are_structurally_validated_and_hashed(
    tmp_path: Path,
) -> None:
    restart_out, particle_file, _ = build_valid_pair(tmp_path)
    fluid_hdf5 = tmp_path / "data.0002.dbl.h5"
    fluid_catalogue = tmp_path / "dbl.h5.out"
    write_fluid_hdf5(fluid_hdf5)
    write_fluid_catalogue(fluid_catalogue)

    result = run_validator(
        restart_out,
        extra_args=[
            "--expected-record-count",
            "3",
            "--expected-output-index",
            str(FLOAT_OUTPUT_SLOT),
            str(FLOAT_RESTART_INDEX),
            "--fluid-hdf5",
            str(fluid_hdf5),
            "--fluid-catalogue",
            str(fluid_catalogue),
            "--fluid-timestep",
            "Timestep_2",
            "--expected-fluid-hdf5-size",
            str(fluid_hdf5.stat().st_size),
            "--expected-fluid-shape",
            "2",
            "3",
            "4",
            "--required-fluid-dataset",
            "rho",
            "--required-fluid-dataset",
            "prs",
            "--required-fluid-dataset",
            "tr1",
            "--required-fluid-dataset",
            "vx1",
            "--required-fluid-dataset",
            "vx2",
            "--required-fluid-dataset",
            "vx3",
            "--expected-fluid-hdf5-sha256",
            hashlib.sha256(fluid_hdf5.read_bytes()).hexdigest(),
            "--hash-inputs",
        ],
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["restart_record_count"] == 3
    assert report["fluid_restart"]["companion_output_indices"] == {"3": 10}
    assert report["fluid_hdf5"]["shape"] == [2, 3, 4]
    assert report["fluid_hdf5"]["time"] == pytest.approx(FLUID_TIME)
    assert report["fluid_hdf5"]["datasets"] == ["rho", "prs", "tr1", "vx1", "vx2", "vx3"]
    assert report["fluid_catalogue"]["index"] == FLUID_RESTART_INDEX
    assert report["fluid_catalogue"]["step"] == PARTICLE_STEP
    assert report["fluid_catalogue"]["time"] == pytest.approx(FLUID_TIME)
    assert report["input_sha256"] == {
        "fluid_catalogue": hashlib.sha256(fluid_catalogue.read_bytes()).hexdigest(),
        "fluid_hdf5": hashlib.sha256(fluid_hdf5.read_bytes()).hexdigest(),
        "particle_restart": hashlib.sha256(particle_file.read_bytes()).hexdigest(),
        "restart_out": hashlib.sha256(restart_out.read_bytes()).hexdigest(),
    }


def test_rejects_fluid_hdf5_sha_that_differs_from_expected_source(
    tmp_path: Path,
) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    fluid_hdf5 = tmp_path / "data.0002.dbl.h5"
    fluid_catalogue = tmp_path / "dbl.h5.out"
    write_fluid_hdf5(fluid_hdf5)
    write_fluid_catalogue(fluid_catalogue)

    result = run_validator(
        restart_out,
        extra_args=[
            "--fluid-hdf5",
            str(fluid_hdf5),
            "--fluid-catalogue",
            str(fluid_catalogue),
            "--fluid-timestep",
            "Timestep_2",
            "--required-fluid-dataset",
            "rho",
            "--expected-fluid-hdf5-sha256",
            "0" * 64,
        ],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "fluid HDF5 SHA-256 mismatch" in result.stderr


def test_rejects_fluid_hdf5_time_that_differs_from_restart_record(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    fluid_hdf5 = tmp_path / "data.0002.dbl.h5"
    fluid_catalogue = tmp_path / "dbl.h5.out"
    write_fluid_hdf5(fluid_hdf5, time=FLUID_TIME + 1.0)
    write_fluid_catalogue(fluid_catalogue)

    result = run_validator(
        restart_out,
        extra_args=[
            "--fluid-hdf5",
            str(fluid_hdf5),
            "--fluid-catalogue",
            str(fluid_catalogue),
            "--fluid-timestep",
            "Timestep_2",
            "--required-fluid-dataset",
            "rho",
        ],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "fluid HDF5 time mismatch" in result.stderr


def test_rejects_fluid_catalogue_step_that_differs_from_restart_record(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)
    fluid_hdf5 = tmp_path / "data.0002.dbl.h5"
    fluid_catalogue = tmp_path / "dbl.h5.out"
    write_fluid_hdf5(fluid_hdf5)
    write_fluid_catalogue(fluid_catalogue, selected_step=PARTICLE_STEP - 1)

    result = run_validator(
        restart_out,
        extra_args=[
            "--fluid-hdf5",
            str(fluid_hdf5),
            "--fluid-catalogue",
            str(fluid_catalogue),
            "--fluid-timestep",
            "Timestep_2",
            "--required-fluid-dataset",
            "rho",
        ],
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "fluid catalogue step mismatch" in result.stderr


@pytest.mark.parametrize(
    "missing_key",
    ["nparticles", "nfields", "nelem", "idCounter", "dt_particles", "time"],
)
def test_rejects_missing_required_particle_metadata(
    tmp_path: Path,
    missing_key: str,
) -> None:
    restart_out, particle_file, _ = build_valid_pair(tmp_path)
    metadata = particle_metadata()
    del metadata[missing_key]
    write_particle_file(particle_file, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: missing required particle header metadata: "
        f"{missing_key}\n"
    )


@pytest.mark.parametrize(
    ("key", "invalid_value"),
    [
        ("nparticles", 0),
        ("nfields", -1),
        ("nelem", 0),
        ("idCounter", -1),
        ("dt_particles", 0.0),
        ("time", float("nan")),
    ],
)
def test_rejects_nonpositive_or_nonfinite_particle_metadata(
    tmp_path: Path,
    key: str,
    invalid_value: object,
) -> None:
    restart_out, particle_file, _ = build_valid_pair(tmp_path)
    metadata = particle_metadata()
    metadata[key] = invalid_value
    write_particle_file(particle_file, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: particle header metadata '{key}' must be "
        "finite and positive\n"
    )


@pytest.mark.parametrize(
    "missing_key",
    [
        "PLUTO_version",
        "dimensions",
        "nflux",
        "endianity",
        "precision",
        "particletype",
        "field_names",
        "field_dim",
    ],
)
def test_rejects_missing_required_particle_identity_and_schema_metadata(
    tmp_path: Path,
    missing_key: str,
) -> None:
    restart_out, particle_file, _ = build_valid_pair(tmp_path)
    metadata = particle_metadata()
    del metadata[missing_key]
    write_particle_file(particle_file, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: missing required particle header metadata: "
        f"{missing_key}\n"
    )


def test_rejects_exact_field_name_schema_mismatch(tmp_path: Path) -> None:
    metadata = particle_metadata()
    names = FIELD_NAMES.copy()
    names[1] = "radius"
    metadata["field_names"] = names
    restart_out, particle_file, _ = build_valid_pair(tmp_path, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: field_names mismatch: expected "
        f"{' '.join(FIELD_NAMES)}, found {' '.join(names)}\n"
    )


def test_rejects_exact_field_dimension_schema_mismatch(tmp_path: Path) -> None:
    metadata = particle_metadata()
    dims = FIELD_DIMS.copy()
    dims[10] = 2
    dims[11] = 2
    metadata["field_dim"] = dims
    restart_out, particle_file, _ = build_valid_pair(tmp_path, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: field_dim mismatch: expected "
        f"{' '.join(str(value) for value in FIELD_DIMS)}, found "
        f"{' '.join(str(value) for value in dims)}\n"
    )


def test_rejects_exact_particle_step_mismatch(tmp_path: Path) -> None:
    metadata = particle_metadata()
    metadata["stepNumber"] = PARTICLE_STEP - 1
    restart_out, particle_file, _ = build_valid_pair(tmp_path, metadata=metadata)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: stepNumber mismatch: expected {PARTICLE_STEP}, "
        f"found {PARTICLE_STEP - 1}\n"
    )


def test_rejects_nonfinite_particle_element(tmp_path: Path) -> None:
    rows = valid_particle_rows()
    rows[1][13] = float("nan")
    restart_out, particle_file, _ = build_valid_pair(tmp_path, rows=rows)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: non-finite particle value at record 1, "
        "field density\n"
    )


def test_rejects_nonintegral_particle_id(tmp_path: Path) -> None:
    rows = valid_particle_rows()
    rows[1][0] = 1.5
    restart_out, particle_file, _ = build_valid_pair(tmp_path, rows=rows)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: particle id 1.5 at record 1 is not integral\n"
    )


def test_rejects_duplicate_particle_id(tmp_path: Path) -> None:
    rows = valid_particle_rows()
    rows[1][0] = 1.0
    restart_out, particle_file, _ = build_valid_pair(tmp_path, rows=rows)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: duplicate particle id 1 at record 1\n"
    )


@pytest.mark.parametrize("invalid_id", [0.0, 3.0])
def test_rejects_particle_id_outside_one_to_idcounter(
    tmp_path: Path,
    invalid_id: float,
) -> None:
    rows = valid_particle_rows()
    rows[1][0] = invalid_id
    restart_out, particle_file, _ = build_valid_pair(tmp_path, rows=rows)

    result = run_validator(restart_out)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        f"error: {particle_file}: particle id {int(invalid_id)} at record 1 is "
        "outside [1, 2]\n"
    )


def test_accepts_optional_named_field_checks(tmp_path: Path) -> None:
    restart_out, _, _ = build_valid_pair(tmp_path)

    result = run_validator(
        restart_out,
        extra_args=[
            "--coordinate-bound",
            "x1",
            "-2",
            "3",
            "--coordinate-bound",
            "x2",
            "-3",
            "1",
            "--nonnegative-field",
            "density",
            "--nonnegative-field",
            "pressure",
            "--time-window-field",
            "tinj",
            "0",
            str(PARTICLE_TIME),
        ],
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("column", "invalid_value", "extra_args", "error_fragment"),
    [
        (
            1,
            3.5,
            ["--coordinate-bound", "x1", "-2", "3"],
            "field x1 value 3.5 at record 1 is outside coordinate bounds [-2.0, 3.0]",
        ),
        (
            13,
            -0.1,
            ["--nonnegative-field", "density"],
            "field density value -0.1 at record 1 must be nonnegative",
        ),
        (
            7,
            PARTICLE_TIME + 1.0,
            ["--time-window-field", "tinj", "0", str(PARTICLE_TIME)],
            f"field tinj value {PARTICLE_TIME + 1.0} at record 1 is outside "
            f"time window [0.0, {PARTICLE_TIME}]",
        ),
    ],
)
def test_rejects_optional_named_field_check_violation(
    tmp_path: Path,
    column: int,
    invalid_value: float,
    extra_args: list[str],
    error_fragment: str,
) -> None:
    rows = valid_particle_rows()
    rows[1][column] = invalid_value
    restart_out, _, _ = build_valid_pair(tmp_path, rows=rows)

    result = run_validator(restart_out, extra_args=extra_args)

    assert result.returncode != 0
    assert result.stdout == ""
    assert error_fragment in result.stderr


@pytest.mark.parametrize(
    ("fluid_output_slot", "particle_output_slot", "invalid_value"),
    [
        (-1, PARTICLE_OUTPUT_SLOT, -1),
        (16, PARTICLE_OUTPUT_SLOT, 16),
        (FLUID_OUTPUT_SLOT, -1, -1),
        (FLUID_OUTPUT_SLOT, 16, 16),
    ],
)
def test_rejects_output_slots_outside_restart_array_bounds(
    tmp_path: Path,
    fluid_output_slot: int,
    particle_output_slot: int,
    invalid_value: int,
) -> None:
    restart_out = tmp_path / "restart.out"
    write_restart_out(restart_out, valid_restart_records())

    result = run_validator(
        restart_out,
        fluid_output_slot=fluid_output_slot,
        particle_output_slot=particle_output_slot,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert f"output slot must be between 0 and 15; got {invalid_value}" in result.stderr


@pytest.mark.parametrize("missing_flag", ["fluid", "particle"])
def test_requires_both_runtime_output_slots(
    tmp_path: Path,
    missing_flag: str,
) -> None:
    restart_out = tmp_path / "restart.out"
    write_restart_out(restart_out, valid_restart_records())
    command = [
        sys.executable,
        str(SCRIPT),
        "--restart-out",
        str(restart_out),
        "--fluid-restart-index",
        str(FLUID_RESTART_INDEX),
    ]
    if missing_flag == "fluid":
        command.extend(["--particle-output-slot", str(PARTICLE_OUTPUT_SLOT)])
    else:
        command.extend(["--fluid-output-slot", str(FLUID_OUTPUT_SLOT)])

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode != 0
    assert result.stdout == ""
    assert f"--{missing_flag}-output-slot" in result.stderr
