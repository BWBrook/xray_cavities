#!/usr/bin/env python3
"""Validate that a PLUTO fluid restart has a compatible particle restart."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


OUTPUT_SLOT_COUNT = 16
RESTART_RECORD = struct.Struct("<17i4x2d40x")
RESTART_RECORD_SIZE = 128
DEFAULT_TIME_ATOL = 0.005
MAX_HEADER_LINE_BYTES = 65_536
REQUIRED_PARTICLE_METADATA = (
    "PLUTO_version",
    "dimensions",
    "nflux",
    "nparticles",
    "nfields",
    "nelem",
    "idCounter",
    "dt_particles",
    "endianity",
    "particletype",
    "precision",
    "time",
    "stepNumber",
    "field_names",
    "field_dim",
)
INTEGER_PARTICLE_METADATA = (
    "dimensions",
    "nflux",
    "nparticles",
    "nfields",
    "nelem",
    "idCounter",
    "particletype",
    "stepNumber",
)


class ValidationError(Exception):
    """A restart pair failed validation."""


@dataclass(frozen=True)
class RestartRecord:
    record_index: int
    nstep: int
    nfiles: tuple[int, ...]
    time: float
    dt: float


@dataclass(frozen=True)
class ParticleHeader:
    header_offset: int
    pluto_version: str
    dimensions: int
    nflux: int
    nparticles: int
    nfields: int
    nelem: int
    id_counter: int
    dt_particles: float
    endianity: str
    particletype: int
    precision: str
    time: float
    step_number: int
    field_names: tuple[str, ...]
    field_dim: tuple[int, ...]


def output_slot(value: str) -> int:
    try:
        slot = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"output slot must be an integer; got {value}") from exc
    if not 0 <= slot < OUTPUT_SLOT_COUNT:
        raise argparse.ArgumentTypeError(
            f"output slot must be between 0 and 15; got {slot}"
        )
    return slot


def nonnegative_index(value: str) -> int:
    try:
        index = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"restart index must be an integer; got {value}"
        ) from exc
    if index < 0:
        raise argparse.ArgumentTypeError(
            f"restart index must be nonnegative; got {index}"
        )
    return index


def positive_integer(value: str) -> int:
    number = nonnegative_index(value)
    if number == 0:
        raise argparse.ArgumentTypeError(f"value must be greater than zero; got {number}")
    return number


def nonnegative_finite_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"atol must be a finite nonnegative number; got {value}"
        ) from exc
    if not math.isfinite(number) or number < 0.0:
        raise argparse.ArgumentTypeError(
            f"atol must be a finite nonnegative number; got {value}"
        )
    return number


def sha256_digest(value: str) -> str:
    digest = value.lower()
    if len(digest) != 64 or any(character not in string.hexdigits for character in digest):
        raise argparse.ArgumentTypeError(
            f"SHA-256 must contain exactly 64 hexadecimal characters; got {value}"
        )
    return digest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PLUTO restart.out fluid/particle restart pairing."
    )
    parser.add_argument(
        "--restart-out",
        required=True,
        type=Path,
        help="Path to the PLUTO restart.out catalogue.",
    )
    parser.add_argument(
        "--fluid-restart-index",
        required=True,
        type=nonnegative_index,
        help="Fluid output index requested for restart.",
    )
    parser.add_argument(
        "--fluid-output-slot",
        required=True,
        type=output_slot,
        help="Runtime output-array slot containing fluid restart indices (0..15).",
    )
    parser.add_argument(
        "--particle-output-slot",
        required=True,
        type=output_slot,
        help="Runtime output-array slot containing particle restart indices (0..15).",
    )
    parser.add_argument(
        "--expected-particle-index",
        type=nonnegative_index,
        help="Optional expected particle index to compare with the selected record.",
    )
    parser.add_argument(
        "--expected-record-count",
        type=positive_integer,
        help="Require restart.out to contain exactly this many 128-byte records.",
    )
    parser.add_argument(
        "--expected-output-index",
        action="append",
        default=[],
        nargs=2,
        metavar=("SLOT", "INDEX"),
        help="Require the selected Restart record to contain INDEX in output SLOT.",
    )
    parser.add_argument(
        "--particle-dir",
        type=Path,
        help="Directory containing particles.NNNN.dbl (defaults to restart.out parent).",
    )
    parser.add_argument(
        "--fluid-hdf5",
        type=Path,
        help="Optional fluid HDF5 checkpoint to bind structurally to the selected record.",
    )
    parser.add_argument(
        "--fluid-catalogue",
        type=Path,
        help="Double-HDF5 catalogue to bind to the selected fluid restart.",
    )
    parser.add_argument(
        "--fluid-timestep",
        help="HDF5 timestep group, required with --fluid-hdf5.",
    )
    parser.add_argument(
        "--expected-fluid-hdf5-size",
        type=positive_integer,
        help="Require the fluid HDF5 file to have this exact byte size.",
    )
    parser.add_argument(
        "--expected-fluid-hdf5-sha256",
        type=sha256_digest,
        help="Require the fluid HDF5 SHA-256 to match a trusted source digest.",
    )
    parser.add_argument(
        "--expected-fluid-shape",
        nargs=3,
        type=positive_integer,
        metavar=("NZ", "NY", "NX"),
        help="Require every requested fluid dataset to have this exact shape.",
    )
    parser.add_argument(
        "--required-fluid-dataset",
        action="append",
        default=[],
        help="Require and scalar-sample this dataset under TIMESTEP/vars.",
    )
    parser.add_argument(
        "--hash-inputs",
        action="store_true",
        help="Record SHA-256 for restart.out, the selected particle file, and fluid HDF5.",
    )
    parser.add_argument(
        "--atol",
        type=nonnegative_finite_float,
        default=DEFAULT_TIME_ATOL,
        help="Absolute fluid/particle time tolerance in code units (default: 0.005).",
    )
    parser.add_argument(
        "--expected-field-names",
        nargs="+",
        help="Require this exact ordered particle field-name schema.",
    )
    parser.add_argument(
        "--expected-field-dims",
        nargs="+",
        type=int,
        help="Require these exact ordered particle field dimensions.",
    )
    parser.add_argument(
        "--expected-step",
        type=nonnegative_index,
        help="Require the particle header to carry this stepNumber.",
    )
    parser.add_argument(
        "--coordinate-bound",
        action="append",
        default=[],
        nargs=3,
        metavar=("FIELD", "MIN", "MAX"),
        help="Require a scalar field to remain within inclusive bounds.",
    )
    parser.add_argument(
        "--nonnegative-field",
        action="append",
        default=[],
        help="Require a scalar field to be nonnegative.",
    )
    parser.add_argument(
        "--time-window-field",
        action="append",
        default=[],
        nargs=3,
        metavar=("FIELD", "MIN", "MAX"),
        help="Require a scalar field to remain within an inclusive time window.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Write the JSON report to this path instead of stdout.",
    )
    return parser.parse_args(argv)


def read_restart_records(path: Path) -> list[RestartRecord]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to read restart.out: {detail}") from exc

    if len(data) % RESTART_RECORD_SIZE != 0:
        raise ValidationError(
            f"{path}: size {len(data)} is not a multiple of the "
            f"{RESTART_RECORD_SIZE}-byte Restart record size"
        )

    records: list[RestartRecord] = []
    for record_index, offset in enumerate(
        range(0, len(data), RESTART_RECORD_SIZE)
    ):
        unpacked = RESTART_RECORD.unpack_from(data, offset)
        records.append(
            RestartRecord(
                record_index=record_index,
                nstep=unpacked[0],
                nfiles=tuple(unpacked[1:17]),
                time=unpacked[17],
                dt=unpacked[18],
            )
        )
    return records


def select_restart_record(
    records: Sequence[RestartRecord],
    *,
    fluid_output_slot: int,
    fluid_restart_index: int,
) -> RestartRecord:
    matches = [
        record
        for record in records
        if record.nfiles[fluid_output_slot] == fluid_restart_index
    ]
    if len(matches) != 1:
        raise ValidationError(
            "expected exactly one Restart record with output slot "
            f"{fluid_output_slot} equal to fluid restart index "
            f"{fluid_restart_index}; found {len(matches)}"
        )
    return matches[0]


def parse_expected_output_indices(
    values: Sequence[Sequence[str]],
) -> list[tuple[int, int]]:
    parsed: list[tuple[int, int]] = []
    seen: set[int] = set()
    for slot_text, index_text in values:
        try:
            slot = int(slot_text)
            index = int(index_text)
        except ValueError as exc:
            raise ValidationError(
                "expected output indices require integer SLOT and INDEX values"
            ) from exc
        if not 0 <= slot < OUTPUT_SLOT_COUNT:
            raise ValidationError(f"output slot must be between 0 and 15; got {slot}")
        if index < 0:
            raise ValidationError(f"restart index must be nonnegative; got {index}")
        if slot in seen:
            raise ValidationError(f"duplicate expected output slot: {slot}")
        seen.add(slot)
        parsed.append((slot, index))
    return parsed


def validate_expected_output_indices(
    record: RestartRecord,
    expected: Sequence[tuple[int, int]],
) -> None:
    for slot, index in expected:
        actual = record.nfiles[slot]
        if actual != index:
            raise ValidationError(
                f"selected Restart record {record.record_index}: output slot {slot} "
                f"contains {actual}, expected {index}"
            )


def validate_restart_metadata(record: RestartRecord) -> None:
    if record.nstep <= 0:
        raise ValidationError(
            f"selected Restart record {record.record_index}: nstep must be positive"
        )
    for name, value in (("time", record.time), ("dt", record.dt)):
        if not math.isfinite(value) or value <= 0.0:
            raise ValidationError(
                f"selected Restart record {record.record_index}: {name} must be "
                "finite and positive"
            )


def _read_ascii_header(path: Path) -> tuple[dict[str, str], int]:
    metadata: dict[str, str] = {}
    header_lines = 0
    header_offset = 0

    try:
        with path.open("rb") as handle:
            while True:
                line_offset = handle.tell()
                marker = handle.read(1)
                if not marker:
                    header_offset = line_offset
                    break
                if marker != b"#":
                    header_offset = line_offset
                    break

                remainder = handle.readline(MAX_HEADER_LINE_BYTES)
                raw_line = marker + remainder
                if not raw_line.endswith(b"\n"):
                    raise ValidationError(
                        f"{path}: unterminated or oversized ASCII particle header line"
                    )
                try:
                    line = raw_line.decode("ascii")
                except UnicodeDecodeError as exc:
                    raise ValidationError(
                        f"{path}: particle header is not ASCII"
                    ) from exc

                header_lines += 1
                header_offset = handle.tell()
                parts = line.split()
                if len(parts) < 2:
                    continue
                if parts[1] == "PLUTO":
                    key = "PLUTO_version"
                    values = parts[2:3]
                else:
                    key = parts[1]
                    values = parts[2:]
                if key not in REQUIRED_PARTICLE_METADATA:
                    continue
                if key in metadata:
                    raise ValidationError(
                        f"{path}: duplicate particle header metadata: {key}"
                    )
                if key not in {"field_names", "field_dim"} and len(values) != 1:
                    raise ValidationError(
                        f"{path}: particle header metadata '{key}' must have one value"
                    )
                if not values:
                    raise ValidationError(
                        f"{path}: particle header metadata '{key}' has no value"
                    )
                metadata[key] = " ".join(values)
    except ValidationError:
        raise
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to read particle file: {detail}") from exc

    if header_lines == 0:
        raise ValidationError(f"{path}: missing ASCII # particle header")
    return metadata, header_offset


def parse_particle_header(path: Path) -> ParticleHeader:
    raw_metadata, header_offset = _read_ascii_header(path)
    missing = [
        key for key in REQUIRED_PARTICLE_METADATA if key not in raw_metadata
    ]
    if missing:
        raise ValidationError(
            f"{path}: missing required particle header metadata: {', '.join(missing)}"
        )

    integer_values: dict[str, int] = {}
    for key in INTEGER_PARTICLE_METADATA:
        try:
            value = int(raw_metadata[key])
        except ValueError as exc:
            raise ValidationError(
                f"{path}: particle header metadata '{key}' must be an integer"
            ) from exc
        if value <= 0:
            raise ValidationError(
                f"{path}: particle header metadata '{key}' must be finite and positive"
            )
        integer_values[key] = value

    float_values: dict[str, float] = {}
    for key in ("dt_particles", "time"):
        try:
            value = float(raw_metadata[key])
        except ValueError as exc:
            raise ValidationError(
                f"{path}: particle header metadata '{key}' must be numeric"
            ) from exc
        if not math.isfinite(value) or value <= 0.0:
            raise ValidationError(
                f"{path}: particle header metadata '{key}' must be finite and positive"
            )
        float_values[key] = value

    field_names = tuple(raw_metadata["field_names"].split())
    try:
        field_dim = tuple(int(value) for value in raw_metadata["field_dim"].split())
    except ValueError as exc:
        raise ValidationError(
            f"{path}: particle header metadata 'field_dim' must contain integers"
        ) from exc
    if any(value <= 0 for value in field_dim):
        raise ValidationError(
            f"{path}: particle header metadata 'field_dim' must contain positive integers"
        )
    if len(field_names) != integer_values["nfields"]:
        raise ValidationError(
            f"{path}: nfields={integer_values['nfields']} but field_names has "
            f"{len(field_names)} entries"
        )
    if len(field_dim) != integer_values["nfields"]:
        raise ValidationError(
            f"{path}: nfields={integer_values['nfields']} but field_dim has "
            f"{len(field_dim)} entries"
        )
    if sum(field_dim) != integer_values["nelem"]:
        raise ValidationError(
            f"{path}: nelem={integer_values['nelem']} but field_dim sums to "
            f"{sum(field_dim)}"
        )
    if raw_metadata["endianity"] != "little":
        raise ValidationError(
            f"{path}: unsupported particle endianity {raw_metadata['endianity']}; "
            "expected little"
        )
    if raw_metadata["precision"] != "double":
        raise ValidationError(
            f"{path}: unsupported particle precision {raw_metadata['precision']}; "
            "expected double"
        )

    return ParticleHeader(
        header_offset=header_offset,
        pluto_version=raw_metadata["PLUTO_version"],
        dimensions=integer_values["dimensions"],
        nflux=integer_values["nflux"],
        nparticles=integer_values["nparticles"],
        nfields=integer_values["nfields"],
        nelem=integer_values["nelem"],
        id_counter=integer_values["idCounter"],
        dt_particles=float_values["dt_particles"],
        endianity=raw_metadata["endianity"],
        particletype=integer_values["particletype"],
        precision=raw_metadata["precision"],
        time=float_values["time"],
        step_number=integer_values["stepNumber"],
        field_names=field_names,
        field_dim=field_dim,
    )


def validate_particle_file_size(path: Path, header: ParticleHeader) -> int:
    try:
        actual_size = path.stat().st_size
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to stat particle file: {detail}") from exc

    expected_size = header.header_offset + header.nparticles * header.nelem * 8
    if actual_size != expected_size:
        raise ValidationError(
            f"particle file size mismatch for {path}: expected {expected_size} bytes "
            f"from header, found {actual_size}"
        )
    return actual_size


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(16 * 1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to hash input: {detail}") from exc
    return digest.hexdigest()


def validate_fluid_hdf5(
    path: Path,
    *,
    timestep: str,
    required_datasets: Sequence[str],
    expected_shape: Sequence[int] | None,
    expected_size: int | None,
    restart_time: float,
    atol: float,
) -> dict[str, object]:
    try:
        actual_size = path.stat().st_size
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to stat fluid HDF5: {detail}") from exc
    if expected_size is not None and actual_size != expected_size:
        raise ValidationError(
            f"fluid HDF5 size mismatch for {path}: expected {expected_size} bytes, "
            f"found {actual_size}"
        )

    try:
        import h5py
    except ImportError as exc:
        raise ValidationError("fluid HDF5 validation requires h5py") from exc

    expected_shape_tuple = tuple(expected_shape) if expected_shape is not None else None
    observed_shape: tuple[int, ...] | None = None
    samples: dict[str, list[float]] = {}
    try:
        with h5py.File(path, "r") as h5:
            if timestep not in h5:
                raise ValidationError(f"{path}: missing HDF5 timestep group {timestep}")
            group = h5[timestep]
            if "Time" not in group.attrs:
                raise ValidationError(f"{path}: {timestep} is missing Time attribute")
            hdf5_time = float(group.attrs["Time"])
            if not math.isfinite(hdf5_time):
                raise ValidationError(f"{path}: {timestep} Time attribute is not finite")
            time_delta = abs(hdf5_time - restart_time)
            if time_delta > atol:
                raise ValidationError(
                    "fluid HDF5 time mismatch: HDF5 time "
                    f"{hdf5_time} and Restart record time {restart_time} differ by "
                    f"{time_delta}, which exceeds atol {atol}"
                )

            for name in required_datasets:
                dataset_path = f"/{timestep}/vars/{name}"
                if dataset_path not in h5:
                    raise ValidationError(f"{path}: missing fluid dataset {dataset_path}")
                dataset = h5[dataset_path]
                shape = tuple(int(value) for value in dataset.shape)
                if not shape or any(value <= 0 for value in shape):
                    raise ValidationError(f"{path}: fluid dataset {dataset_path} is empty")
                if observed_shape is None:
                    observed_shape = shape
                elif shape != observed_shape:
                    raise ValidationError(
                        f"{path}: fluid dataset shape mismatch: {dataset_path} has "
                        f"{shape}, expected {observed_shape}"
                    )
                if expected_shape_tuple is not None and shape != expected_shape_tuple:
                    raise ValidationError(
                        f"{path}: fluid dataset {dataset_path} has shape {shape}, "
                        f"expected {expected_shape_tuple}"
                    )
                first = float(dataset[tuple(0 for _ in shape)])
                last = float(dataset[tuple(value - 1 for value in shape)])
                if not math.isfinite(first) or not math.isfinite(last):
                    raise ValidationError(
                        f"{path}: fluid dataset {dataset_path} has a non-finite scalar sample"
                    )
                samples[name] = [first, last]
    except ValidationError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationError(f"{path}: unable to validate fluid HDF5: {exc}") from exc

    if observed_shape is None:
        raise ValidationError("fluid HDF5 validation requires at least one dataset")
    return {
        "datasets": list(required_datasets),
        "path": str(path),
        "scalar_samples_first_last": samples,
        "shape": list(observed_shape),
        "size_bytes": actual_size,
        "time": hdf5_time,
        "time_delta": time_delta,
        "timestep": timestep,
    }


def validate_fluid_catalogue(
    path: Path,
    *,
    fluid_restart_index: int,
    restart_time: float,
    restart_step: int,
    atol: float,
) -> dict[str, object]:
    matches: list[tuple[float, float, int]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                fields = line.split()
                if not fields or not fields[0].isdigit():
                    continue
                if int(fields[0]) != fluid_restart_index:
                    continue
                if len(fields) < 4:
                    raise ValidationError(
                        f"{path}: matching fluid catalogue row {line_number} has fewer "
                        "than four fields"
                    )
                try:
                    time_value = float(fields[1])
                    dt_value = float(fields[2])
                    step_value = int(fields[3])
                except ValueError as exc:
                    raise ValidationError(
                        f"{path}: matching fluid catalogue row {line_number} has "
                        "invalid time, dt, or step"
                    ) from exc
                if (
                    not math.isfinite(time_value)
                    or not math.isfinite(dt_value)
                    or time_value <= 0.0
                    or dt_value <= 0.0
                    or step_value <= 0
                ):
                    raise ValidationError(
                        f"{path}: matching fluid catalogue row {line_number} must "
                        "contain finite positive time, dt, and step"
                    )
                matches.append((time_value, dt_value, step_value))
    except ValidationError:
        raise
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to read fluid catalogue: {detail}") from exc

    if len(matches) != 1:
        raise ValidationError(
            f"{path}: expected exactly one numeric row for fluid restart index "
            f"{fluid_restart_index}, found {len(matches)}"
        )
    time_value, dt_value, step_value = matches[0]
    time_delta = abs(time_value - restart_time)
    if time_delta > atol:
        raise ValidationError(
            "fluid catalogue time mismatch: catalogue time "
            f"{time_value} and Restart record time {restart_time} differ by "
            f"{time_delta}, which exceeds atol {atol}"
        )
    if step_value != restart_step:
        raise ValidationError(
            f"fluid catalogue step mismatch: catalogue step {step_value} does not "
            f"match Restart record nstep {restart_step}"
        )
    return {
        "dt": dt_value,
        "index": fluid_restart_index,
        "path": str(path),
        "step": step_value,
        "time": time_value,
        "time_delta": time_delta,
    }


def validate_particle_schema(
    path: Path,
    header: ParticleHeader,
    *,
    expected_field_names: Sequence[str] | None,
    expected_field_dims: Sequence[int] | None,
    expected_step: int | None,
) -> None:
    if expected_field_names is not None:
        expected_names = tuple(expected_field_names)
        if header.field_names != expected_names:
            raise ValidationError(
                f"{path}: field_names mismatch: expected {' '.join(expected_names)}, "
                f"found {' '.join(header.field_names)}"
            )
    if expected_field_dims is not None:
        expected_dims = tuple(expected_field_dims)
        if header.field_dim != expected_dims:
            raise ValidationError(
                f"{path}: field_dim mismatch: expected "
                f"{' '.join(str(value) for value in expected_dims)}, found "
                f"{' '.join(str(value) for value in header.field_dim)}"
            )
    if expected_step is not None and header.step_number != expected_step:
        raise ValidationError(
            f"{path}: stepNumber mismatch: expected {expected_step}, "
            f"found {header.step_number}"
        )


def _field_layout(header: ParticleHeader) -> tuple[dict[str, tuple[int, int]], list[str]]:
    layout: dict[str, tuple[int, int]] = {}
    element_names: list[str] = []
    offset = 0
    for name, dimension in zip(header.field_names, header.field_dim, strict=True):
        if name in layout:
            raise ValidationError(f"duplicate particle field name: {name}")
        layout[name] = (offset, dimension)
        element_names.extend([name] * dimension)
        offset += dimension
    return layout, element_names


def _require_scalar_field(
    path: Path,
    layout: dict[str, tuple[int, int]],
    field: str,
) -> int:
    if field not in layout:
        raise ValidationError(f"{path}: requested particle field is absent: {field}")
    offset, dimension = layout[field]
    if dimension != 1:
        raise ValidationError(
            f"{path}: requested particle field {field} is not scalar "
            f"(dimension {dimension})"
        )
    return offset


def validate_particle_content(
    path: Path,
    header: ParticleHeader,
    *,
    coordinate_bounds: Sequence[tuple[str, float, float]],
    nonnegative_fields: Sequence[str],
    time_window_fields: Sequence[tuple[str, float, float]],
) -> dict[str, int]:
    layout, element_names = _field_layout(header)
    id_offset = _require_scalar_field(path, layout, "id")
    coordinate_checks = [
        (_require_scalar_field(path, layout, field), field, lower, upper)
        for field, lower, upper in coordinate_bounds
    ]
    nonnegative_checks = [
        (_require_scalar_field(path, layout, field), field)
        for field in nonnegative_fields
    ]
    time_checks = [
        (_require_scalar_field(path, layout, field), field, lower, upper)
        for field, lower, upper in time_window_fields
    ]

    record_struct = struct.Struct(f"<{header.nelem}d")
    ids: set[int] = set()
    id_min: int | None = None
    id_max: int | None = None
    try:
        with path.open("rb") as handle:
            handle.seek(header.header_offset)
            for record_index in range(header.nparticles):
                raw = handle.read(record_struct.size)
                if len(raw) != record_struct.size:
                    raise ValidationError(
                        f"{path}: truncated particle payload at record {record_index}"
                    )
                values = record_struct.unpack(raw)
                for field_index, value in enumerate(values):
                    if not math.isfinite(value):
                        raise ValidationError(
                            f"{path}: non-finite particle value at record "
                            f"{record_index}, field {element_names[field_index]}"
                        )

                id_value = values[id_offset]
                if not id_value.is_integer():
                    raise ValidationError(
                        f"{path}: particle id {id_value} at record {record_index} "
                        "is not integral"
                    )
                particle_id = int(id_value)
                if not 1 <= particle_id <= header.id_counter:
                    raise ValidationError(
                        f"{path}: particle id {particle_id} at record {record_index} "
                        f"is outside [1, {header.id_counter}]"
                    )
                if particle_id in ids:
                    raise ValidationError(
                        f"{path}: duplicate particle id {particle_id} at record "
                        f"{record_index}"
                    )
                ids.add(particle_id)
                id_min = particle_id if id_min is None else min(id_min, particle_id)
                id_max = particle_id if id_max is None else max(id_max, particle_id)

                for offset, field, lower, upper in coordinate_checks:
                    value = values[offset]
                    if not lower <= value <= upper:
                        raise ValidationError(
                            f"{path}: field {field} value {value} at record "
                            f"{record_index} is outside coordinate bounds "
                            f"[{lower}, {upper}]"
                        )
                for offset, field in nonnegative_checks:
                    value = values[offset]
                    if value < 0.0:
                        raise ValidationError(
                            f"{path}: field {field} value {value} at record "
                            f"{record_index} must be nonnegative"
                        )
                for offset, field, lower, upper in time_checks:
                    value = values[offset]
                    if not lower <= value <= upper:
                        raise ValidationError(
                            f"{path}: field {field} value {value} at record "
                            f"{record_index} is outside time window [{lower}, {upper}]"
                        )
    except ValidationError:
        raise
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to read particle payload: {detail}") from exc

    if len(ids) != header.nparticles or id_min is None or id_max is None:
        raise ValidationError(
            f"{path}: particle ID count does not match nparticles={header.nparticles}"
        )
    return {
        "id_max": id_max,
        "id_min": id_min,
        "records_scanned": header.nparticles,
        "unique_ids": len(ids),
    }


def parse_named_ranges(
    values: Sequence[Sequence[str]],
    *,
    label: str,
) -> list[tuple[str, float, float]]:
    parsed: list[tuple[str, float, float]] = []
    for field, lower_text, upper_text in values:
        try:
            lower = float(lower_text)
            upper = float(upper_text)
        except ValueError as exc:
            raise ValidationError(
                f"{label} for {field} must use numeric bounds"
            ) from exc
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise ValidationError(
                f"{label} for {field} must use finite ordered bounds"
            )
        parsed.append((field, lower, upper))
    return parsed


def validate_restart_pair(
    *,
    restart_out: Path,
    fluid_restart_index: int,
    fluid_output_slot: int,
    particle_output_slot: int,
    expected_particle_index: int | None = None,
    expected_record_count: int | None = None,
    expected_output_indices: Sequence[tuple[int, int]] = (),
    particle_dir: Path | None = None,
    fluid_hdf5: Path | None = None,
    fluid_catalogue: Path | None = None,
    fluid_timestep: str | None = None,
    expected_fluid_hdf5_size: int | None = None,
    expected_fluid_hdf5_sha256: str | None = None,
    expected_fluid_shape: Sequence[int] | None = None,
    required_fluid_datasets: Sequence[str] = (),
    hash_inputs: bool = False,
    atol: float = DEFAULT_TIME_ATOL,
    expected_field_names: Sequence[str] | None = None,
    expected_field_dims: Sequence[int] | None = None,
    expected_step: int | None = None,
    coordinate_bounds: Sequence[tuple[str, float, float]] = (),
    nonnegative_fields: Sequence[str] = (),
    time_window_fields: Sequence[tuple[str, float, float]] = (),
) -> dict[str, object]:
    restart_out = restart_out.expanduser()
    records = read_restart_records(restart_out)
    if expected_record_count is not None and len(records) != expected_record_count:
        raise ValidationError(
            f"{restart_out}: expected exactly {expected_record_count} Restart records, "
            f"found {len(records)}"
        )
    record = select_restart_record(
        records,
        fluid_output_slot=fluid_output_slot,
        fluid_restart_index=fluid_restart_index,
    )
    validate_restart_metadata(record)
    validate_expected_output_indices(record, expected_output_indices)

    particle_index = record.nfiles[particle_output_slot]
    if particle_index < 0:
        raise ValidationError(
            f"selected Restart record {record.record_index}: output slot "
            f"{particle_output_slot} does not contain a particle restart index "
            f"(found {particle_index})"
        )
    if (
        expected_particle_index is not None
        and particle_index != expected_particle_index
    ):
        raise ValidationError(
            "particle restart index mismatch: output slot "
            f"{particle_output_slot} contains {particle_index}, expected "
            f"{expected_particle_index}"
        )

    particle_root = (
        particle_dir.expanduser() if particle_dir is not None else restart_out.parent
    )
    particle_file = particle_root / f"particles.{particle_index:04d}.dbl"
    particle_header = parse_particle_header(particle_file)
    particle_size = validate_particle_file_size(particle_file, particle_header)
    validate_particle_schema(
        particle_file,
        particle_header,
        expected_field_names=expected_field_names,
        expected_field_dims=expected_field_dims,
        expected_step=expected_step,
    )
    if particle_header.step_number != record.nstep:
        raise ValidationError(
            f"{particle_file}: stepNumber {particle_header.step_number} does not match "
            f"selected Restart record nstep {record.nstep}"
        )
    content = validate_particle_content(
        particle_file,
        particle_header,
        coordinate_bounds=coordinate_bounds,
        nonnegative_fields=nonnegative_fields,
        time_window_fields=time_window_fields,
    )

    time_delta = abs(particle_header.time - record.time)
    if time_delta > atol:
        raise ValidationError(
            "particle time mismatch: particle time "
            f"{particle_header.time} and fluid time {record.time} differ by "
            f"{time_delta}, which exceeds atol {atol}"
        )

    fluid_hdf5_report: dict[str, object] | None = None
    fluid_catalogue_report: dict[str, object] | None = None
    fluid_hdf5_sha256: str | None = None
    if fluid_hdf5 is not None:
        if not fluid_timestep:
            raise ValidationError("--fluid-timestep is required with --fluid-hdf5")
        if fluid_catalogue is None:
            raise ValidationError("--fluid-catalogue is required with --fluid-hdf5")
        if not required_fluid_datasets:
            raise ValidationError(
                "at least one --required-fluid-dataset is required with --fluid-hdf5"
            )
        fluid_hdf5 = fluid_hdf5.expanduser()
        fluid_hdf5_report = validate_fluid_hdf5(
            fluid_hdf5,
            timestep=fluid_timestep,
            required_datasets=required_fluid_datasets,
            expected_shape=expected_fluid_shape,
            expected_size=expected_fluid_hdf5_size,
            restart_time=record.time,
            atol=atol,
        )
        fluid_catalogue = fluid_catalogue.expanduser()
        fluid_catalogue_report = validate_fluid_catalogue(
            fluid_catalogue,
            fluid_restart_index=fluid_restart_index,
            restart_time=record.time,
            restart_step=record.nstep,
            atol=atol,
        )
        if hash_inputs or expected_fluid_hdf5_sha256 is not None:
            fluid_hdf5_sha256 = sha256_file(fluid_hdf5)
        if (
            expected_fluid_hdf5_sha256 is not None
            and fluid_hdf5_sha256 != expected_fluid_hdf5_sha256
        ):
            raise ValidationError(
                "fluid HDF5 SHA-256 mismatch: expected source digest "
                f"{expected_fluid_hdf5_sha256}, found {fluid_hdf5_sha256}"
            )
    elif any(
        value is not None
        for value in (
            fluid_catalogue,
            fluid_timestep,
            expected_fluid_hdf5_size,
            expected_fluid_hdf5_sha256,
            expected_fluid_shape,
        )
    ) or required_fluid_datasets:
        raise ValidationError("fluid HDF5 options require --fluid-hdf5")

    fluid_restart_report: dict[str, object] = {
        "dt": record.dt,
        "index": fluid_restart_index,
        "nstep": record.nstep,
        "output_slot": fluid_output_slot,
        "record_index": record.record_index,
        "time": record.time,
    }
    if expected_output_indices:
        fluid_restart_report["companion_output_indices"] = {
            str(slot): index for slot, index in expected_output_indices
        }

    report: dict[str, object] = {
        "fluid_restart": {
            **fluid_restart_report,
        },
        "particle_restart": {
            "PLUTO_version": particle_header.pluto_version,
            "content": content,
            "dimensions": particle_header.dimensions,
            "dt_particles": particle_header.dt_particles,
            "endianity": particle_header.endianity,
            "field_dim": list(particle_header.field_dim),
            "field_names": list(particle_header.field_names),
            "header_offset": particle_header.header_offset,
            "idCounter": particle_header.id_counter,
            "index": particle_index,
            "nelem": particle_header.nelem,
            "nfields": particle_header.nfields,
            "nflux": particle_header.nflux,
            "nparticles": particle_header.nparticles,
            "output_slot": particle_output_slot,
            "path": str(particle_file),
            "particletype": particle_header.particletype,
            "precision": particle_header.precision,
            "size_bytes": particle_size,
            "stepNumber": particle_header.step_number,
            "time": particle_header.time,
        },
        "restart_out": str(restart_out),
        "status": "ok",
        "time_atol": atol,
        "time_delta": time_delta,
    }
    if expected_record_count is not None:
        report["restart_record_count"] = len(records)
    if fluid_hdf5_report is not None:
        report["fluid_hdf5"] = fluid_hdf5_report
    if fluid_catalogue_report is not None:
        report["fluid_catalogue"] = fluid_catalogue_report
    if hash_inputs:
        input_sha256 = {
            "particle_restart": sha256_file(particle_file),
            "restart_out": sha256_file(restart_out),
        }
        if fluid_hdf5 is not None:
            input_sha256["fluid_hdf5"] = fluid_hdf5_sha256 or sha256_file(fluid_hdf5)
        if fluid_catalogue is not None:
            input_sha256["fluid_catalogue"] = sha256_file(fluid_catalogue)
        report["input_sha256"] = input_sha256
    return report


def render_json(report: dict[str, object]) -> str:
    return json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n"


def emit_report(text: str, json_output: Path | None) -> None:
    if json_output is None:
        sys.stdout.write(text)
        return
    path = json_output.expanduser()
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValidationError(f"{path}: unable to write JSON output: {detail}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        expected_output_indices = parse_expected_output_indices(
            args.expected_output_index
        )
        coordinate_bounds = parse_named_ranges(
            args.coordinate_bound,
            label="coordinate bound",
        )
        time_window_fields = parse_named_ranges(
            args.time_window_field,
            label="time window",
        )
        report = validate_restart_pair(
            restart_out=args.restart_out,
            fluid_restart_index=args.fluid_restart_index,
            fluid_output_slot=args.fluid_output_slot,
            particle_output_slot=args.particle_output_slot,
            expected_particle_index=args.expected_particle_index,
            expected_record_count=args.expected_record_count,
            expected_output_indices=expected_output_indices,
            particle_dir=args.particle_dir,
            fluid_hdf5=args.fluid_hdf5,
            fluid_catalogue=args.fluid_catalogue,
            fluid_timestep=args.fluid_timestep,
            expected_fluid_hdf5_size=args.expected_fluid_hdf5_size,
            expected_fluid_hdf5_sha256=args.expected_fluid_hdf5_sha256,
            expected_fluid_shape=args.expected_fluid_shape,
            required_fluid_datasets=args.required_fluid_dataset,
            hash_inputs=args.hash_inputs,
            atol=args.atol,
            expected_field_names=args.expected_field_names,
            expected_field_dims=args.expected_field_dims,
            expected_step=args.expected_step,
            coordinate_bounds=coordinate_bounds,
            nonnegative_fields=args.nonnegative_field,
            time_window_fields=time_window_fields,
        )
        emit_report(render_json(report), args.json_output)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
