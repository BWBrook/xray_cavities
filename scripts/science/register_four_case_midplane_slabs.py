"""Bind the 18 slab extractions to the sealed full-depth controls, maps and masks."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

AXES = ("horizontal_axis_kpc", "horizontal_edges_kpc", "z_axis_kpc", "z_edges_kpc")
RADIAL = "observer_refit__deficit_threshold_observer_radial_0.05__retained_linear__v0"
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def register(archive, evidence, local):
    seal = json.loads((evidence / "seal.json").read_bytes())
    seal_sha = digest((evidence / "seal.json").read_bytes())
    archive_sha = json.loads((evidence / "archive_verification.json").read_bytes())["archive_sha256"]
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != archive_sha:
            raise ValueError("The source archive differs from the published receipt")
    with (evidence / "native_inputs.csv").open() as stream:
        native = {(r["case"], int(r["snapshot_index"])): r for r in csv.DictReader(stream)}
    units = {(r["case"], r["snapshot_index"], r["view_deg"]): r for r in seal["units"]}
    controls, rows = {}, []
    with tarfile.open(archive, "r:") as tar:
        def member(name, expected, retain=False):
            data = tar.extractfile(name).read()
            if digest(data) != expected:
                raise ValueError("Sealed archive member differs: " + name)
            if retain:
                destination = local / name
                destination.parent.mkdir(exist_ok=True, parents=True)
                destination.write_bytes(data)
            return data

        for case in CASES:
            for age in (0, *AGES):
                if case == "G-HI" and age in (20, 50):
                    continue
                name = f"{case}_{age:04d}"
                source = native[case, age]
                front, side = (units[case, age, angle] for angle in (0, 90))
                producer = front["producer_receipt_sha256"]
                if side["producer_receipt_sha256"] != producer or source["native_input_receipt_sha256"] != front["source_receipt_sha256"]:
                    raise ValueError("Inconsistent archive identities: " + name)
                receipt = json.loads(member(f"producer_receipts/{name}.json", producer, True))
                contract = source["producer_contract_sha256"]
                member(f"contracts/{name}.json", contract)
                for view in (front, side):
                    if receipt["files"][view["file"]]["sha256"] != view["maps_sha256"]:
                        raise ValueError("Producer and seal differ: " + view["file"])
                side_data = member("map_inputs/" + side["file"], side["maps_sha256"], True)
                with np.load(io.BytesIO(side_data), allow_pickle=False) as side_map:
                    side_fields = set(side_map.files)
                if "brightness_current_retained_linear_whole" not in side_fields:
                    raise ValueError("No archived whole-gas field: " + name)
                mask_file = member("predictions/" + front["file"], front["prediction_sha256"])
                with np.load(io.BytesIO(mask_file), allow_pickle=False) as masks:
                    mask = np.ascontiguousarray(masks[RADIAL], dtype=bool)
                if age == 0:
                    initial = member("map_inputs/" + front["file"], front["maps_sha256"])
                    with np.load(io.BytesIO(initial), allow_pickle=False) as image:
                        data = image["brightness_current_retained_linear_whole"]
                        axes_sha = {k: digest(np.ascontiguousarray(image[k]).tobytes()) for k in AXES}
                    if mask.any():
                        raise ValueError("Published full-depth null has a selection: " + name)
                    controls[case] = {
                        "previous_producer_sha256": producer, "full_initial_raster_sha256": front["maps_sha256"],
                        "brightness_sha256": digest(np.ascontiguousarray(data).tobytes()), "shape": list(data.shape),
                        "dtype": str(data.dtype), "axes_sha256": axes_sha, "selected_full_depth_pixels": int(mask.sum()),
                    }
                    continue
                rows.append({
                    "case": case, "snapshot_index": age, "case_age": name,
                    "actual_age_myr": float(source["actual_age_myr"]), "contract_sha256": contract,
                    "previous_producer_sha256": producer,
                    "initial_previous_producer_sha256": controls[case]["previous_producer_sha256"],
                    "sealed_radial_mask_sha256": digest(mask.tobytes()),
                    "archive_90_sha256": side["maps_sha256"],
                    "archive_90_fields": sorted(k for k in side_fields if k.startswith("brightness_") and "retained_linear" in k),
                })
    if len(rows) != 18 or len(controls) != 4:
        raise ValueError("Unexpected case-age panel")
    return {"source_archive_sha256": archive_sha, "prediction_seal_sha256": seal_sha,
            "radial_mask_key": RADIAL, "full_depth_controls": controls, "science": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--local-reference-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = register(args.archive, args.evidence, args.local_reference_dir)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
