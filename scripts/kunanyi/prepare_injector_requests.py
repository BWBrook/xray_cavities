"""Bind the injector diagnostic to the four accepted native histories and calibration inputs."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(archive, destination):
    fixed_dirs = {
        "C-HI": "turn18_high_review_2026-11-18/stage",
        "C-LO": "turn18_clo_review_2026-11-16/capture/stage",
        "G-HI": "turn18_high_review_2026-11-18/stage",
        "G-LO": "turn18_glo_fixed_2026-11-18/stage",
    }
    calibration = archive / "turn19_nozzle_calibration/inputs"
    axes_receipt = json.loads((calibration / "axes_manifest.json").read_text())
    for case, subdir in fixed_dirs.items():
        fixed = archive / subdir / "results" / f"fixed_{case}_full"
        binding_file = fixed / "request_binding.json"
        bindings = json.loads(binding_file.read_text())["preflights"]
        target = destination / case
        target.mkdir(parents=True, exist_ok=True)
        history = []
        static = bindings["0"]["files"]
        table = next((calibration / case).glob("tabulated_*.csv"))
        input_hashes = {"atmosphere.csv": (table, static["environment"]["sha256"]),
                        "pluto.ini": (calibration / case / "pluto.ini", static["runtime_config"]["sha256"]),
                        "axes.npz": (calibration / case / "axes.npz", axes_receipt["cases"][case]["raw_sha256"])}
        for name, (source, expected) in input_hashes.items():
            if digest(source) != expected:
                raise ValueError(f"{case}: calibration identity differs for {name}")
            shutil.copyfile(source, target / name)
        for index, node in enumerate(bindings["0"]["chain"]):
            snapshot_file = fixed / f"snapshot_{index:04d}.json"
            snap = json.loads(snapshot_file.read_text())
            claims = snap["provenance"]["input_receipt_claims"]
            identity = claims["inputs"]["current_h5"]
            selected = bindings[str(index)]["chain"][index]
            if (case != snap["case"] or index != snap["snapshot_index"] or index != node["index"]
                    or selected != node or node["timestep"] != claims["current"]["timestep"]
                    or node["time_code"] != claims["current"]["time_code"]
                    or any(identity[k] != node["metadata"][k]
                           for k in ("resolved_path", "size_bytes", "inode", "mtime_ns", "ctime_ns"))):
                raise ValueError(f"Native identity disagreement at {case}/{index}")
            history.append(dict(index=index, timestep=node["timestep"], time_code=node["time_code"],
                                age_myr=snap["actual_time_myr"], shape=snap["shape_nz_ny_nx"],
                                fixed_receipt_sha256=digest(snapshot_file), native=identity))
        if len(history) != (48 if case == "G-HI" else 51) or len(bindings) != len(history):
            raise ValueError(f"Incomplete history for {case}")
        request = dict(case=case, request_binding_sha256=digest(binding_file), history=history,
                       static_sha256={k: v[1] for k, v in input_hashes.items()})
        (target / "request.json").write_text(json.dumps(request, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.private_archive, args.destination)
