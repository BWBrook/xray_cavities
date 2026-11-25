"""Bind unchanged X-ray images, exact tracer depths and archived radial detections.

Private rasters are read in memory. The registered initial targets describe an
empty evolved cavity; their physical nozzle footprint needs a native projection.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

import compare_compressive_front as front
from run_background_refit_blind import AXES, load_config, side_score, validate_axes
from summarise_heldout_xray import CUSTODY, METHODS, SCIENCE, SIDES, read_scores, verify_archive


IMAGE = "brightness_current_retained_linear_whole"
TRACER_PATH = "path_C_kpc"
METHOD = METHODS[1]
BASELINE_KEY = f"observer_refit__{METHOD}__retained_linear__v0"
FRONT = SCIENCE / "assets/compressive_front_observer_2026-11-23"
FRONT_COMPARISON_SHA = "3d8752d647cf50475c5838568eaac3cd3cb060de0863271947a75a005f61500b"
DET05_SEAL_SHA = "5e917a299e83c5693e01f2c8dbf787213aa99e322aac77ebf5ad11d48a4244ce"
PREDICTION_VERIFICATION_SHA = "e38bd0321dfeca7d862ddffc7347383b3ae01a593837a27254ee27c90d4a41c6"
TARGET_CUSTODY_SHA = "d9b07a83c65173d2b03e5a224d5c64abd20a2ca4db36882a38f72f7c73ca70b5"


@dataclass
class SourceView:
    unit_id: str
    case: str
    snapshot_index: int
    view_deg: int
    kind: str
    actual_age_myr: float
    axes: dict
    image: np.ndarray
    initial_image: np.ndarray
    target_path_kpc: np.ndarray
    baseline_mask: np.ndarray
    baseline_rows: dict
    native_volume_kpc3: dict
    qualification_holds: list
    provenance: dict
    historical_mask: np.ndarray | None = None
    historical_rows: dict | None = None
    historical_detector_z_axis_kpc: np.ndarray | None = None

    @property
    def fit_tracer_path_kpc(self):
        """Physical tracer depth when the archived evaluation target actually preserves it."""
        return None if self.kind == "initial_null" else self.target_path_kpc


def verified_member(archive, name, digest):
    with archive.extractfile(name) as stream:
        data = stream.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"{name}: archive member digest differs")
    return data


def read_fields(archive, name, digest, *fields):
    data = verified_member(archive, name, digest)
    with np.load(io.BytesIO(data), allow_pickle=False) as source:
        return {key: source[key] for key in (*AXES, *fields)}


def native_sources(producer):
    return {record["role"] + "_sha256": record["sha256"] for record in producer["provenance"]["native_inputs"]}


def volumes(uid, axes, path, image, initial, mask, physical, kind):
    _, he, z, ze = validate_axes(axes, image.shape)
    if (any(a.shape != image.shape for a in (initial, mask, path)) or mask.dtype != bool
            or any(not np.isfinite(a).all() for a in (image, initial, path)) or np.any(path < 0)):
        raise ValueError(f"{uid}: invalid image, mask or tracer depth")
    cell_volume = path * np.outer(np.diff(ze), np.diff(he))
    if np.any(cell_volume[z == 0]):
        raise ValueError(f"{uid}: tracer on unassigned hemisphere midplane")
    result = {side: float(cell_volume[half].sum()) for side, half in zip(SIDES, (z < 0, z > 0), strict=True)}
    result["both"] = sum(result.values())
    if not np.isfinite(physical) or physical <= 0 or (kind == "initial_null" and result["both"] != 0):
        raise ValueError(f"{uid}: scoring target and physical tracer have inconsistent initial semantics")
    if kind != "initial_null" and not np.isclose(result["both"], physical, rtol=1e-10, atol=0):
        raise ValueError(f"{uid}: detector grid loses native tracer volume")
    return result


def check_metrics(uid, archived, measured):
    for name, value in measured.items():
        recorded = archived[name]
        if isinstance(value, (float, np.floating)):
            matches = bool(recorded) and np.isclose(float(recorded), value, rtol=1e-12, atol=1e-13)
        else:
            matches = recorded == ("" if value is None else str(value))
        if not matches:
            raise ValueError(f"{uid}/{archived['hemisphere']}: archived {name} differs from the original raster")


def development_views(directory):
    verify_archive(FRONT / "comparison_receipt.json", FRONT_COMPARISON_SHA)
    comparison = json.loads((FRONT / "comparison_receipt.json").read_text())
    inputs = comparison["observer_input_hashes"]
    stats = FRONT / "replacement_recovery.csv"
    verify_archive(stats, comparison["products"][stats.name])
    with stats.open(newline="") as stream:
        rows = {(int(r["view_deg"]), r["comparison"], r["hemisphere"]): r
                for r in csv.DictReader(stream) if r["method"] == METHOD}
    verify_archive(directory / "completion.json", inputs["source_receipt_sha256"])
    producer = json.loads((directory / "completion.json").read_text())
    native = native_sources(producer)
    if native != {k + "_sha256": v for k, v in inputs["native_source_sha256"].items()}:
        raise ValueError("G-HI/20: development native identities differ")
    for angle in front.ANGLES:
        uid = f"G-HI_0020_{angle}deg"
        archive = directory / f"{uid}.npz"
        digest = inputs["view_map_sha256"][str(angle)]
        verify_archive(archive, digest)
        if producer["files"][archive.name]["sha256"] != digest:
            raise ValueError(f"{uid}: development producer and comparison digests differ")
        with np.load(archive, allow_pickle=False) as data:
            axes = {key: data[key] for key in AXES}
            image, initial = data[IMAGE], data["brightness_initial_retained_linear_whole"]
            path = data[TRACER_PATH]
            mask = data[f"mask_retained_linear_v100_{METHOD}_exact_projection_refit"]
            historical = data[f"original_mask_{METHOD}"]
        projection = producer["projection"][str(angle)]
        physical = projection["native_volume_integrals"][TRACER_PATH]
        volume = volumes(uid, axes, path, image, initial, mask, physical, "development")
        old_z = front.original_z_axis(directory, producer, angle)
        grid = front.Grid(*(axes[key] for key in AXES))
        baseline, original = {}, {}
        for side, half in zip(SIDES, (grid.z[:, None] < 0, grid.z[:, None] > 0), strict=True):
            for name, selected, table in (("exact_refit_background", mask, baseline),
                                          ("original", historical, original)):
                table[side] = rows[angle, name, side]
                check_metrics(uid, table[side], front.recovery_metrics(grid, selected, path, half, historical))
        provenance = {**native, "producer_receipt_sha256": inputs["source_receipt_sha256"],
                      "maps_sha256": digest, "initial_maps_sha256": digest, "truth_sha256": digest,
                      "baseline_sha256": digest, "baseline_table_sha256": comparison["products"][stats.name],
                      "physical_native_lobe_kpc3": physical, "geometry": projection["projection_geometry"],
                      "historical_detector_z_sha256": producer["provenance"]["compact_inputs"][f"view{angle}_vertical"]["sha256"]}
        yield SourceView(uid, "G-HI", 20, angle, "development", producer["actual_time_myr"],
                         axes, image, initial, path, mask, baseline, volume,
                         producer["scientific_qualification"]["holds"], provenance, historical, original, old_z)


def registered_views(prediction_tar, truth_tar):
    verify_archive(CUSTODY / "private_scoring_custody.json", TARGET_CUSTODY_SHA)
    verify_archive(CUSTODY / "archive_verification.json", PREDICTION_VERIFICATION_SHA)
    custody = json.loads((CUSTODY / "private_scoring_custody.json").read_text())
    release = custody["release"]
    verification = json.loads((CUSTODY / "archive_verification.json").read_text())
    if release["seal_sha256"] != DET05_SEAL_SHA or verification["seal_sha256"] != DET05_SEAL_SHA:
        raise ValueError("DET-05 custody and original seal differ")
    verify_archive(prediction_tar, verification["archive_sha256"])
    verify_archive(truth_tar, release["archive_sha256"])
    with tarfile.open(prediction_tar, "r:") as predictions, tarfile.open(truth_tar, "r:") as targets:
        seal = json.loads(verified_member(predictions, "seal.json", DET05_SEAL_SHA))
        manifest_sha = seal["scoring_manifest_commitment_sha256"]
        if manifest_sha != release["scoring_manifest_sha256"]:
            raise ValueError("DET-05 scoring manifest differs from the original commitment")
        manifest = json.loads(verified_member(targets, "scoring_truth_manifest.json", manifest_sha))
        truth = {u["unit_id"]: u for u in manifest["units"]}
        units = {u["unit_id"]: u for u in seal["units"]}
        if set(truth) != set(units) or len(truth) != 66:
            raise ValueError("DET-05 unit inventory differs")
        config = SCIENCE.parents[1] / "configs/background_refit_blind_2026-11-11.json"
        verify_archive(config, seal["protocol_config_sha256"])
        criteria = load_config(config)["criteria"]
        scores = {(r["unit_id"], r["hemisphere"]): r for r in read_scores(seal, custody)
                  if r["key"] == BASELINE_KEY}
        initial_maps = {}
        for uid, unit in units.items():
            case, index, angle, kind = (unit[k] for k in ("case", "snapshot_index", "view_deg", "kind"))
            tag = f"{case}_{index:04d}"
            target = truth[uid]
            td = target["truth"]["sha256"]
            if (any(target[k] != unit[k] for k in ("case", "snapshot_index", "view_deg", "kind"))
                    or target["provenance"]["native_input_receipt"]["sha256"] != unit["source_receipt_sha256"]
                    or target["provenance"]["producer_receipt"]["sha256"] != unit["producer_receipt_sha256"]):
                raise ValueError(f"{uid}: scoring and prediction provenance differ")
            producer = json.loads(verified_member(predictions, f"producer_receipts/{tag}.json", unit["producer_receipt_sha256"]))
            source = json.loads(verified_member(predictions, f"native_receipts/{tag}.json", unit["source_receipt_sha256"]))
            native = native_sources(producer)
            if (any(native[k + "_sha256"] != r["sha256"] for k, r in source["inputs"].items())
                    or producer["provenance"]["native_input_receipt"]["sha256"] != unit["source_receipt_sha256"]
                    or producer["files"][uid + ".truth.npz"]["sha256"] != td
                    or producer["files"][unit["file"]]["sha256"] != unit["maps_sha256"]):
                raise ValueError(f"{uid}: native receipts or producer files differ")
            current = read_fields(predictions, "map_inputs/" + unit["file"], unit["maps_sha256"], IMAGE)
            first_uid = f"{case}_0000_{angle}deg"
            first = units[first_uid]
            if first_uid not in initial_maps:
                initial_maps[first_uid] = (current if uid == first_uid else
                    read_fields(predictions, "map_inputs/" + first["file"], first["maps_sha256"], IMAGE))
            initial = initial_maps[first_uid]
            masks = read_fields(predictions, "predictions/" + unit["file"], unit["prediction_sha256"], BASELINE_KEY)
            target_fields = read_fields(targets, f"truth/{uid}.truth.npz", td, TRACER_PATH)
            axes = {k: current[k] for k in AXES}
            if any(not np.array_equal(axes[k], a[k]) for k in AXES for a in (initial, masks, target_fields)):
                raise ValueError(f"{uid}: initial image, mask or target grid differs from current")
            path, mask = target_fields[TRACER_PATH], masks[BASELINE_KEY]
            projection = producer["projection"][str(angle)]
            physical = projection["native_integrals"][TRACER_PATH]
            volume = volumes(uid, axes, path, current[IMAGE], initial[IMAGE], mask, physical, kind)
            baseline = {side: scores[uid, side] for side in SIDES}
            holds = target["qualification_holds"]
            if producer["scientific_qualification"]["holds"] != holds:
                raise ValueError(f"{uid}: producer and target qualifications differ")
            for side, row in baseline.items():
                if json.loads(row["qualification_holds"]) != holds:
                    raise ValueError(f"{uid}: score and target qualifications differ")
                check_metrics(uid, row, side_score(mask, path > 0, axes, side, kind, criteria))
            provenance = {**native, "producer_receipt_sha256": unit["producer_receipt_sha256"],
                          "source_receipt_sha256": unit["source_receipt_sha256"], "maps_sha256": unit["maps_sha256"],
                          "initial_maps_sha256": first["maps_sha256"], "truth_sha256": td,
                          "baseline_sha256": unit["prediction_sha256"], "baseline_table_sha256": release["scores_sha256"],
                          "physical_native_lobe_kpc3": physical, "geometry": projection["geometry"]}
            yield SourceView(uid, case, index, angle, kind, producer["actual_time_myr"], axes, current[IMAGE],
                             initial[IMAGE], path, mask, baseline, volume, holds, provenance)


def iter_source_views(exposed_dir, prediction_tar, truth_tar, *, include_exposed=True, include_registered=True):
    """Yield the three exposed views first, then the 66 DET-05 science and control views.

    AXES gives detector centres and physical integration edges in horizontal, z
    order. The historical G-HI/20 mask used the retained text z centres; its
    archived scores both then and here use the exact pixel areas and edges.
    """
    if include_exposed:
        yield from development_views(Path(exposed_dir))
    if include_registered:
        yield from registered_views(Path(prediction_tar), Path(truth_tar))
