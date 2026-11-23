"""Verify the public commitment against the original prediction inputs, without scoring."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
from numpy.lib import format as npy

import assemble_blind_emission_cohort as assembler
import prepare_blind_emission_maps as producer
import run_background_refit_blind as frozen


# Frozen on 11 November at c352554. The map adapter and assembler were
# independently frozen at f1218f1.
CONFIG_SHA256 = "aaef89201ec5e4ab7fd792b754a66b8463e9ed71756ad33e55d22f84bf9844b8"
PRODUCER_SHA256 = "d84be77567aad949599c1ce0d3be7186990352898ee89fd22507538107ad6bf1"
ASSEMBLER_SHA256 = "1ebd7c631d78861e92c6ea38a0bfc6bc3b39bf9c7c5f7c5dbc249be727e2a981"


def array_headers(path, fields):
    with zipfile.ZipFile(path) as archive:
        if sorted(archive.namelist()) != sorted(name + ".npy" for name in fields):
            raise ValueError(f"{path.name}: array inventory differs")
        headers = {}
        for name in fields:
            with archive.open(name + ".npy") as member:
                version = npy.read_magic(member)
                if version == (1, 0):
                    shape, _, dtype = npy.read_array_header_1_0(member)
                elif version == (2, 0):
                    shape, _, dtype = npy.read_array_header_2_0(member)
                else:
                    raise ValueError(f"{path.name}: unexpected NPY version")
                headers[name] = (shape, dtype)
    return headers


def check_member_layout(map_path, prediction_path, labels):
    keys = [label["key"] for label in labels]
    map_headers = array_headers(map_path, producer.DETECTOR_FIELDS)
    pred_headers = array_headers(prediction_path, [*frozen.AXES, *keys])
    h, _, z, _ = frozen.AXES
    shape = (map_headers[z][0][0], map_headers[h][0][0])
    for name in producer.DETECTOR_FIELDS:
        if name not in frozen.AXES and (map_headers[name][0] != shape or map_headers[name][1].kind != "f"):
            raise ValueError(f"{map_path.name}: invalid detector input header {name}")
    for key in keys:
        if pred_headers[key] != (shape, np.dtype(bool)):
            raise ValueError(f"{prediction_path.name}: invalid mask header {key}")
    with np.load(map_path, allow_pickle=False) as maps, np.load(prediction_path, allow_pickle=False) as preds:
        axes = {name: maps[name] for name in frozen.AXES}
        frozen.validate_axes(axes, shape)
        if any(pred_headers[name] != map_headers[name] or not np.array_equal(axes[name], preds[name])
               for name in frozen.AXES):
            raise ValueError(f"{prediction_path.name}: prediction and input coordinates differ")


def audit(seal_path: Path, maps_path: Path, predictions: Path, config_path: Path) -> dict:
    if maps_path.name != "maps_manifest.json" or seal_path.name != "seal.json":
        raise ValueError("provide seal.json and the prediction-only maps_manifest.json")
    receipt_path = predictions / "prediction_receipt.json"
    seal, receipt, maps = (frozen.read_json(path) for path in (seal_path, receipt_path, maps_path))
    if (frozen.digest(config_path) != CONFIG_SHA256 or frozen.digest(producer.__file__) != PRODUCER_SHA256
            or frozen.digest(assembler.__file__) != ASSEMBLER_SHA256):
        raise ValueError("audit configuration or producer/assembler differs from the reviewed commits")
    config = frozen.load_config(config_path)
    assembly_path = maps_path.with_name("assembly_receipt.json")
    assembly = frozen.read_json(assembly_path)
    inventory_path = maps_path.parent.parent / "producer_inventory.json"
    if (seal["assembly_receipt_sha256"] != frozen.digest(assembly_path)
            or seal["producer_inventory_sha256"] != frozen.digest(inventory_path)
            or assembly["inventory_sha256"] != seal["producer_inventory_sha256"]
            or assembly["files"]["maps_manifest.json"]["sha256"] != seal["maps_manifest_sha256"]
            or assembly["files"]["scoring_truth_manifest.json"]["sha256"] != seal["scoring_manifest_commitment_sha256"]
            or assembly["scoring_truth_released"] is not False
            or seal["scoring_truth_arrays_evaluated"] is not False
            or datetime.fromisoformat(seal["protected_before_prediction_utc"]) >
               datetime.fromisoformat(seal["utc_after_validation"])):
        raise ValueError("assembly, protected truth commitment or recorded ordering differs")
    if (seal["protocol_config_sha256"] != CONFIG_SHA256 or receipt["config_sha256"] != CONFIG_SHA256
            or maps["protocol_config"]["sha256"] != CONFIG_SHA256
            or seal["frozen_runner_sha256"] != config["runner_sha256"]
            or receipt["runner_sha256"] != config["runner_sha256"]
            or seal["producer_source_sha256"] != PRODUCER_SHA256 or seal["assembler_sha256"] != ASSEMBLER_SHA256
            or frozen.digest(receipt_path) != seal["prediction_receipt_sha256"]
            or frozen.digest(maps_path) != seal["maps_manifest_sha256"]
            or receipt["input_manifest_sha256"] != seal["maps_manifest_sha256"]
            or receipt["status"] != "predictions_sealed_before_scoring"
            or seal["scoring_truth_released"] is not False or receipt["scoring_truth_read"] is not False):
        raise ValueError("public commitment, prediction receipt or input manifest differs")
    frozen.validate_labels(config, seal["label_definitions"])
    for record in (seal, maps, receipt):
        frozen.validate_units(config, record["units"])
    inputs = {row["unit_id"]: row for row in maps["units"]}
    outputs = {row["unit_id"]: row for row in receipt["units"]}
    filenames = {"prediction_receipt.json"}
    sources = {}
    for public in seal["units"]:
        uid = public["unit_id"]
        src, out = inputs[uid], outputs[uid]
        name = f"{public['case']}_{public['snapshot_index']:04d}_{public['view_deg']}deg.npz"
        map_record = src["maps"]
        map_path = Path(map_record["path"])
        pred_path = predictions / name
        if (set(src) != {"unit_id", "case", "snapshot_index", "view_deg", "kind", "maps",
                         "provenance", "qualification_holds"} or frozen.unit_key(public) != frozen.unit_key(src)
                or frozen.unit_key(src) != frozen.unit_key(out) or out["provenance"] != src["provenance"]
                or src["qualification_holds"] != out["qualification_holds"] or name != uid + ".npz"
                or map_path.name != name or public["file"] != name or out["predictions"] != name):
            raise ValueError(f"{uid}: unit identity, filename or producer qualifications differ")
        for ref, public_key in (("native_input_receipt", "source_receipt_sha256"),
                                ("producer_receipt", "producer_receipt_sha256")):
            if public[public_key] != src["provenance"][ref]["sha256"]:
                raise ValueError(f"{uid}: receipt digest differs")
        # These functions open the two source JSON receipts and validate their
        # contents. No truth payload or manifest is an input to this audit.
        for ref in src["provenance"].values():
            location = Path(ref["path"])
            if location.is_symlink() or location.suffix != ".json" or "truth" in location.name.lower():
                raise ValueError(f"{uid}: input provenance must refer to native and producer JSON receipts")
        frozen.bind_provenance(src)
        native_ref, producer_ref = (src["provenance"][key] for key in ("native_input_receipt", "producer_receipt"))
        pair = (public["case"], public["snapshot_index"])
        producer_receipt = frozen.read_json(producer_ref["path"])
        source_hashes = (native_ref["sha256"], producer_ref["sha256"])
        if pair in sources and sources[pair] != source_hashes:
            raise ValueError(f"{uid}: native or producer receipt changes between azimuths")
        if pair not in sources:
            assembler.bind_producer_metadata(producer_receipt, frozen.read_json(native_ref["path"]), config, CONFIG_SHA256)
            sources[pair] = source_hashes
        if (map_record["sha256"] != out["input_sha256"] or map_record["sha256"] != public["maps_sha256"]
                or map_path.is_symlink() or frozen.digest(map_path) != public["maps_sha256"]
                or pred_path.is_symlink() or frozen.digest(pred_path) != public["prediction_sha256"]
                or out["prediction_sha256"] != public["prediction_sha256"]
                or pred_path.stat().st_size != public["size_bytes"]):
            raise ValueError(f"{uid}: map or prediction payload differs")
        frozen.validate_labels(config, out["labels"])
        check_member_layout(map_path, pred_path, out["labels"])
        filenames.add(name)
    if {p.name for p in predictions.iterdir()} != filenames:
        raise ValueError("prediction directory inventory differs")
    science = sum(row["kind"] == "science" for row in seal["units"])
    inventory = frozen.read_json(inventory_path)["producers"]
    pinned_pairs = {(row["native_input_receipt"]["sha256"], row["producer_receipt"]["sha256"]) for row in inventory}
    if len(inventory) != len(sources) or pinned_pairs != set(sources.values()):
        raise ValueError("original producer inventory and predicted unit provenance differ")
    counts = (science, len(inputs)-science, len(sources), len(inputs)*len(seal["label_definitions"]))
    if counts != (seal["science_views"], seal["initial_null_views"], seal["producer_count"], seal["prediction_masks"]):
        raise ValueError("published census differs")
    return {"seal_sha256": frozen.digest(seal_path), "prediction_receipt_sha256": frozen.digest(receipt_path),
            "science_views": science, "null_views": len(inputs) - science, "producer_pairs": len(sources),
            "prediction_masks": len(inputs) * len(seal["label_definitions"]), "pixel_values_examined": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--maps-manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.seal, args.maps_manifest, args.predictions, args.config), indent=2))
