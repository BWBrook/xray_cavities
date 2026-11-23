import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

from test_assemble_blind_emission_cohort import CONFIG, ROOT, inventory

sys.path.insert(0, str(ROOT / "scripts/kunanyi"))
import seal_blind_emission_predictions as sealer
import audit_xray_prediction_seal as auditor


def test_complete_custody_audit_without_truth_access(inventory, tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    slots = []
    for entry in json.loads(inventory.read_text())["producers"]:
        original = Path(entry["producer_receipt"]["path"])
        record = json.loads(original.read_text())
        pair = f"{record['case']}_{record['snapshot_index']:04d}"
        dest = stage / "products" / pair
        shutil.copytree(original.parent, dest)
        record["provenance"]["contract"] = {"sha256": "a" * 64}
        (dest / "completion.json").write_text(json.dumps(record))
        slots.append({**{k: record[k] for k in ("case", "snapshot_index", "kind")},
                      "native_input_receipt": entry["native_input_receipt"], "contract": record["provenance"]["contract"]})
    slot_path = stage / "slots.json"
    slot_path.write_text(json.dumps(slots))
    config = auditor.frozen.load_config(CONFIG)
    monkeypatch.setattr(sealer.blind, "observer_masks",
                        lambda image, h, z: {m: np.zeros_like(image, dtype=bool) for m in config["methods"]})
    output = tmp_path / "sealed"
    sealer.seal(stage, CONFIG, slot_path, output)
    seal_path = output / "seal.json"
    maps = output / "manifests/maps_manifest.json"
    predictions = output / "predictions"
    original_open = Path.open

    def only_unprotected(path, *args, **kwargs):
        assert "truth" not in path.name.lower(), path
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", only_unprotected)
    result = auditor.audit(seal_path, maps, predictions, CONFIG)
    assert (result["science_views"], result["null_views"], result["producer_pairs"], result["prediction_masks"]) == (54, 12, 22, 1056)
    publication = tmp_path / "public"
    publication.mkdir()
    record = json.loads(seal_path.read_text())
    record["units"][0]["maps_sha256"] = "e" * 64
    (publication / "seal.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="payload differs"):
        auditor.audit(publication / "seal.json", maps, predictions, CONFIG)
    # Restore only fixture permissions so pytest can remove the temporary directory.
    predictions.chmod(0o700)


def test_header_check_rejects_a_shifted_coordinate_or_nonboolean_mask(tmp_path):
    axes = {n: np.arange(4 if "edges" in n else 3, dtype=float) for n in auditor.frozen.AXES}
    for key in ("z_axis_kpc", "horizontal_axis_kpc"):
        axes[key] += 0.5
    fields = {n: np.zeros((3, 3)) for n in auditor.producer.DETECTOR_FIELDS if n not in axes}
    source, target = tmp_path / "maps.npz", tmp_path / "prediction.npz"
    np.savez(source, **axes, **fields)
    pred = {**axes, "m": np.ones((3, 3), dtype=bool)}
    np.savez(target, **{**pred, "z_axis_kpc": axes["z_axis_kpc"] + 0.1})
    with pytest.raises(ValueError, match="coordinates differ"):
        auditor.check_member_layout(source, target, [{"key": "m"}])
    np.savez(target, **{**pred, "m": pred["m"].astype(float)})
    with pytest.raises(ValueError, match="invalid mask header"):
        auditor.check_member_layout(source, target, [{"key": "m"}])


def test_precommit_binds_each_new_readout_to_the_original_native_fields(tmp_path):
    native, production, manifest = (tmp_path / name for name in ("native.json", "completion.json", "maps_manifest.json"))
    material = ["current_h5", "initial_h5", "environment", "grid_file"]
    fields = {name: {"sha256": str(i) * 64} for i, name in enumerate(material)}
    native.write_text(json.dumps({"inputs": fields}))
    production.write_text(json.dumps({"actual_time_myr": 10.001,
        "provenance": {"contract": {"sha256": "c" * 64}, "native_preflight_contract": {"sha256": "d" * 64},
                       "inherited_lineage_receipt": None}}))
    native_hash = auditor.frozen.digest(native)
    unit = {"case": "C-HI", "snapshot_index": 10, "kind": "science",
            "provenance": {"native_input_receipt": {"path": str(native), "sha256": native_hash},
                           "producer_receipt": {"path": str(production), "sha256": auditor.frozen.digest(production)}}}
    manifest.write_text(json.dumps({"units": [{**unit, "view_deg": i} for i in (0,45,90)]}))
    register = tmp_path / "native_inputs.csv"
    row = {"case": "C-HI", "snapshot_index": 10, "kind": "science", "actual_age_myr": 10.001,
           "producer_contract_sha256": "c"*64, "native_preflight_contract_sha256": "d"*64,
           "native_input_receipt_sha256": native_hash, "lineage_sha256": ""}
    for name in material:
        row[("atmosphere" if name == "environment" else name) + "_sha256"] = fields[name]["sha256"]
    with register.open("w", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    assert auditor.check_registered_inputs(register, manifest, auditor.frozen.digest(register)) == 1
    fields["initial_h5"]["sha256"] = "f"*64
    native.write_text(json.dumps({"inputs": fields}))
    with pytest.raises(ValueError, match="original initial_h5 digest differs"):
        auditor.check_registered_inputs(register, manifest, auditor.frozen.digest(register))
