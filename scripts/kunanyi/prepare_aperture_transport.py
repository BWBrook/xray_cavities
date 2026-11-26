"""Bind moving-aperture measurements to the reviewed native stock and injector histories."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/science"))
from build_tracer_mass_budget import FIXED
from compare_fixed_histories import RECEIPTS

STOCKS = ROOT / "docs/science/assets/turn15_review_2026-11-11/budgets"
REGIONS = ("R100", "R300")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def prepare(archive, native_requests, work, public_file):
    report = {"method": "native cell-centre velocity apertures on existing signed stock histories", "cases": {}}
    for case, subdir in FIXED.items():
        fixed = archive / subdir / f"fixed_{case}_full"
        completion_path = fixed / "completion.json"
        if sha(completion_path) != RECEIPTS[case]:
            raise ValueError(f"{case}: fixed stock completion changed")
        completion = json.loads(completion_path.read_bytes())
        products = {Path(row["path"]).name: row["sha256"] for row in completion["products"]}
        request_path = native_requests / case / "request.json"
        request = json.loads(request_path.read_bytes())
        indices = list(range(48 if case == "G-HI" else 51))
        if (request["case"] != case or [r["index"] for r in request["history"]] != indices
                or completion["indices"] != indices):
            raise ValueError(f"{case}: native or stock history is incomplete")
        csv_path = STOCKS / case / "measurements.csv"
        with csv_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        published = {(int(r["snapshot_index"]), "R" + r["speed_threshold_km_s"]): r for r in rows}
        if len(rows) != len(published) or set(published) != {(i, n) for i in indices for n in REGIONS}:
            raise ValueError(f"{case}: incomplete or duplicated radius history")
        stage = work / case
        stage.mkdir(parents=True, exist_ok=True)
        for name, expected in request["static_sha256"].items():
            path = native_requests / case / name
            if sha(path) != expected:
                raise ValueError(f"{case}: changed static input {name}")
            shutil.copyfile(path, stage / name)
        with np.load(stage / "axes.npz", allow_pickle=False) as axes:
            x, y, z = (axes[k][abs(axes[k]) <= 0.75] for k in "xyz")
            radius = np.sqrt((y[:, None]**2 + x[None, :]**2) + z[:, None, None]**2)
            source_cells = radius[radius <= 0.75]
        if source_cells.size != 14328:
            raise ValueError(f"{case}: grid differs from the measured injector sphere")
        records = []
        for row in request["history"]:
            i = row["index"]
            path = fixed / f"snapshot_{i:04d}.json"
            if sha(path) != products[path.name] or products[path.name] != row["fixed_receipt_sha256"]:
                raise ValueError(f"{case}/{i}: native and fixed snapshot bindings disagree")
            snap = json.loads(path.read_bytes())
            inputs = snap["provenance"]["input_receipt_claims"]["inputs"]
            if (snap["case"] != case or snap["snapshot_index"] != i or snap["shape_nz_ny_nx"] != row["shape"]
                    or inputs["current_h5"] != row["native"]
                    or inputs["initial_h5"]["sha256"] != request["history"][0]["native"]["sha256"]
                    or inputs["environment"]["sha256"] != request["static_sha256"]["atmosphere.csv"]):
                raise ValueError(f"{case}/{i}: inconsistent native identity")
            apertures = {}
            for name in REGIONS:
                geometry = snap["speed_apertures"][name]
                ref = published[i, name]
                radius = geometry["raw_radius_kpc"]
                if (ref["case"] != case or float(ref["actual_time_myr"]) != row["age_myr"]
                        or snap["actual_time_myr"] != row["age_myr"] or float(ref["raw_radius_kpc"]) != radius):
                    raise ValueError(f"{case}/{i}/{name}: published time or radius differs")
                stock = snap["regions"][name]["partitions"]["all"]
                if radius < max(source_cells):
                    raise ValueError(f"{case}/{i}/{name}: the aperture omits maintained cells")
                apertures[name] = {**geometry, "cell_count": stock["cell_count"], "volume_kpc3": stock["volume_kpc3"],
                                   "stock": {k: stock[k] for k in ("mass_delta_g", "thermal_delta_erg", "kinetic_delta_erg",
                                                                   "gravitational_delta_erg", "total_delta_erg")}}
            records.append({"index": i, "age_myr": row["age_myr"], "fixed_sha256": products[path.name],
                            "native_sha256": row["native"]["sha256"], "apertures": apertures})
        case_record = {"fixed_completion_sha256": RECEIPTS[case], "input_request_sha256": sha(request_path),
                       "published_radius_table_sha256": sha(csv_path), "static_sha256": request["static_sha256"],
                       "maintained_cells": int(source_cells.size), "max_maintained_radius_kpc": float(max(source_cells)),
                       "snapshots": records}
        report["cases"][case] = case_record
        shutil.copyfile(request_path, stage / "request.json")
    public_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(public_file, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("archive", "native_requests", "work", "public_file"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    prepare(args.archive, args.native_requests, args.work, args.public_file)
