#!/usr/bin/env python3
"""Build the final C-HI Level 3 ambient-energy method package."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


SIDES = ("negative_z", "positive_z", "bipolar_total")
REQUIRED_DATASETS = ("rho", "prs", "tr1", "vx1", "vx2", "vx3")
DEFAULT_TRACER_THRESHOLD = 5.0e-3

DEFAULT_REMOTE_PREFLIGHT = {
    "baseline_h5": (
        "/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/"
        "C-HI/particles/problem/outputs/data.0000.flt.h5"
    ),
    "baseline_timestep": "Timestep_0",
    "final_h5": (
        "/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/"
        "C-HI/particles/problem/outputs/data.0051.flt.h5"
    ),
    "final_timestep": "Timestep_51",
    "baseline_shape_nz_ny_nx": [1014, 960, 960],
    "final_shape_nz_ny_nx": [1014, 960, 960],
    "required_datasets": list(REQUIRED_DATASETS),
    "baseline_datasets": list(REQUIRED_DATASETS),
    "final_datasets": list(REQUIRED_DATASETS),
    "verification_route": "Open OnDemand shell read-only HDF5 preflight",
}

DEFAULT_PV_ERG = 6.87805393912703e59
DEFAULT_TWO_POINT_FIVE_PV_ERG = 1.7195134847817576e60
DEFAULT_FOUR_PV_ERG = 2.751221575650812e60


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_metric_csv(path: Path) -> dict[str, dict[str, str]]:
    return {row["metric"]: row for row in read_rows(path)}


def parse_float(value: Any, *, context: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{context} must be finite")
    return out


def threshold_matches(value: str, expected: float = DEFAULT_TRACER_THRESHOLD) -> bool:
    observed = parse_float(value, context="threshold")
    return math.isclose(observed, expected, rel_tol=0.0, abs_tol=expected * 1.0e-8)


def write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate_grid_preflight(preflight: dict[str, Any]) -> None:
    baseline_shape = list(preflight.get("baseline_shape_nz_ny_nx", []))
    final_shape = list(preflight.get("final_shape_nz_ny_nx", []))
    if baseline_shape != final_shape:
        raise ValueError(f"grid shapes differ: baseline={baseline_shape} final={final_shape}")

    required = set(preflight.get("required_datasets") or REQUIRED_DATASETS)
    baseline = set(preflight.get("baseline_datasets", []))
    final = set(preflight.get("final_datasets", []))
    missing_baseline = sorted(required - baseline)
    missing_final = sorted(required - final)
    if missing_baseline:
        raise ValueError(f"missing baseline datasets: {', '.join(missing_baseline)}")
    if missing_final:
        raise ValueError(f"missing final datasets: {', '.join(missing_final)}")


def load_comparators(
    *,
    level1_path: Path,
    level2_path: Path,
    pV_erg: float,
    two_point_five_pV_erg: float,
    four_pV_erg: float,
) -> dict[str, float]:
    level1 = read_metric_csv(level1_path)
    if "injected_energy_bipolar_elapsed" not in level1:
        raise ValueError("missing Level 1 injected_energy_bipolar_elapsed")
    level1_energy = parse_float(
        level1["injected_energy_bipolar_elapsed"]["value"],
        context="Level 1 injected_energy_bipolar_elapsed",
    )

    level2_rows = read_rows(level2_path)
    level2_energy = None
    for row in level2_rows:
        if row.get("side") == "bipolar_total" and threshold_matches(row.get("threshold", "")):
            level2_energy = parse_float(row["total_energy_erg"], context="Level 2 bipolar total energy")
            break
    if level2_energy is None:
        raise ValueError("missing Level 2 bipolar_total row at tracer threshold 5e-3")

    return {
        "level1_bipolar_injected_erg": level1_energy,
        "level2_bipolar_lobe_erg": level2_energy,
        "pV_bipolar_erg": parse_float(pV_erg, context="pV_erg"),
        "two_point_five_pV_bipolar_erg": parse_float(
            two_point_five_pV_erg,
            context="two_point_five_pV_erg",
        ),
        "four_pV_bipolar_erg": parse_float(four_pV_erg, context="four_pV_erg"),
    }


def safe_ratio(value: float | None, denominator: float) -> float | str:
    if value is None:
        return ""
    if denominator == 0.0:
        return ""
    return value / denominator


def ratio_fields(value: float | None, comparators: dict[str, float]) -> dict[str, float | str]:
    return {
        "ratio_to_level1_bipolar_injected": safe_ratio(value, comparators["level1_bipolar_injected_erg"]),
        "ratio_to_level2_bipolar_lobe": safe_ratio(value, comparators["level2_bipolar_lobe_erg"]),
        "ratio_to_pV_bipolar": safe_ratio(value, comparators["pV_bipolar_erg"]),
        "ratio_to_2.5pV_bipolar": safe_ratio(value, comparators["two_point_five_pV_bipolar_erg"]),
        "ratio_to_4pV_bipolar": safe_ratio(value, comparators["four_pV_bipolar_erg"]),
    }


def energy_row(
    *,
    side: str,
    component: str,
    status: str,
    value: float | None,
    unit: str,
    comparators: dict[str, float],
    note: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "side": side,
        "component": component,
        "status": status,
        "value_erg": value if value is not None else "",
        "unit": unit,
        "note": note,
    }
    row.update(ratio_fields(value, comparators))
    return row


def build_energy_rows(
    *,
    extractor_rows: list[dict[str, str]] | None,
    comparators: dict[str, float],
    gravitational_status: str,
    gravitational_note: str,
    thermal_kinetic_blocker: str = "blocked_remote_postprocessing_access",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if extractor_rows:
        for source in extractor_rows:
            side = source["side"]
            thermal = parse_float(source["thermal_delta_erg"], context=f"{side} thermal_delta_erg")
            kinetic = parse_float(source["kinetic_delta_erg"], context=f"{side} kinetic_delta_erg")
            rows.append(
                energy_row(
                    side=side,
                    component="ambient_thermal_delta",
                    status="computed",
                    value=thermal,
                    unit="erg",
                    comparators=comparators,
                    note="Final ambient cells minus matching baseline cells.",
                )
            )
            rows.append(
                energy_row(
                    side=side,
                    component="ambient_kinetic_delta",
                    status="computed",
                    value=kinetic,
                    unit="erg",
                    comparators=comparators,
                    note="Final ambient cells minus matching baseline cells.",
                )
            )
            rows.append(
                energy_row(
                    side=side,
                    component="ambient_thermal_plus_kinetic_delta",
                    status="computed",
                    value=thermal + kinetic,
                    unit="erg",
                    comparators=comparators,
                    note="Thermal plus kinetic ambient-medium energy change.",
                )
            )
    else:
        for component in ("ambient_thermal_delta", "ambient_kinetic_delta", "ambient_thermal_plus_kinetic_delta"):
            rows.append(
                energy_row(
                    side="bipolar_total",
                    component=component,
                    status=thermal_kinetic_blocker,
                    value=None,
                    unit="erg",
                    comparators=comparators,
                    note=(
                        "Baseline and final fields exist and the streaming extractor is tested locally, "
                        "but bounded remote post-processing has not completed."
                    ),
                )
            )

    rows.append(
        energy_row(
            side="bipolar_total",
            component="ambient_gravitational_delta",
            status=gravitational_status,
            value=None,
            unit="erg",
            comparators=comparators,
            note=gravitational_note,
        )
    )
    return rows


def method_decision_rows(*, preflight: dict[str, Any], gravitational_status: str) -> list[dict[str, str]]:
    return [
        {
            "decision": "baseline_reference",
            "status": "identified",
            "choice": f"{preflight['baseline_h5']}::{preflight['baseline_timestep']}",
            "rationale": "Earliest full-grid initial output from the same C-HI production chain found remotely.",
        },
        {
            "decision": "final_endpoint",
            "status": "identified",
            "choice": f"{preflight['final_h5']}::{preflight['final_timestep']}",
            "rationale": "Accepted final 50 Myr C-HI endpoint used by Goals 003, 005, and 007.",
        },
        {
            "decision": "grid_compatibility",
            "status": "preflight_passed",
            "choice": f"shape {preflight['final_shape_nz_ny_nx']}",
            "rationale": "Baseline and final expose matching rho/prs/tr1/vx1/vx2/vx3 datasets and grid shape.",
        },
        {
            "decision": "coordinate_compatibility",
            "status": "enforced_by_extractor_not_remote_preflight",
            "choice": "compare baseline/final X, Y, and Z coordinate axes with rtol=0 and atol=1e-10 kpc",
            "rationale": (
                "Remote preflight observed only shape and dataset presence; the extractor now fails fast "
                "before subtraction if coordinate axes differ."
            ),
        },
        {
            "decision": "ambient_tracer_exclusion",
            "status": "selected",
            "choice": "final cells with tr1 <= 5e-3 are ambient; tr1 > 5e-3 remains Level 2 lobe truth",
            "rationale": "Keeps Level 3 compatible with the accepted Level 2 tracer-lobe threshold.",
        },
        {
            "decision": "spatial_mask",
            "status": "selected",
            "choice": "whole-grid side-aware mask, split by z < 0 and z >= 0 plus bipolar total",
            "rationale": "Captures shocked ambient gas outside the tracer-defined lobes without adding a new cavity geometry.",
        },
        {
            "decision": "thermal_formula",
            "status": "ready_for_bounded_postprocessing",
            "choice": "sum((prs_final - prs_baseline) * dV / (gamma - 1)) * unit_energy",
            "rationale": "Matches the pressure-volume unit convention in pluto_h5_truth_extract.c.",
        },
        {
            "decision": "kinetic_formula",
            "status": "ready_for_bounded_postprocessing",
            "choice": "sum(0.5 * (rho_final*v_final^2 - rho_baseline*v_baseline^2) * dV) * unit_energy",
            "rationale": "Uses the same PLUTO code-unit energy conversion as Level 2 truth.",
        },
        {
            "decision": "thermal_kinetic_extractor",
            "status": "tested_local_ready_not_run_remote",
            "choice": "scripts/science/pluto_h5_level3_ambient_extract.py",
            "rationale": "Synthetic-HDF5 tests validate the final tracer mask, grid-shape check, and thermal/kinetic sums.",
        },
        {
            "decision": "remote_postprocessing_access",
            "status": "blocked_remote_postprocessing_access",
            "choice": "terminal SSH/SCP denied at jumpbox after Open OnDemand enablement; OOD web shell allowed read-only preflight",
            "rationale": "Full-grid extraction needs bounded Kunanyi post-processing and reliable staging/retrieval.",
        },
        {
            "decision": "gravitational_component",
            "status": gravitational_status,
            "choice": "not computed in Goal 008",
            "rationale": "The accepted HDF5 vars do not include potential, and no reviewed potential/profile convention is in this repo.",
        },
    ]


def result_status(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row["status"]) for row in rows}
    if "computed" in statuses and "blocked_missing_potential" in statuses:
        return "partial_green_with_gravitational_blocker"
    if "blocked_remote_postprocessing_access" in statuses:
        return "blocked_remote_postprocessing_access"
    if statuses == {"computed"}:
        return "green_for_c_hi_endpoint_review"
    return "_and_".join(sorted(statuses))


def build_package(
    *,
    output_dir: Path,
    level1_path: Path,
    level2_path: Path,
    pV_erg: float,
    two_point_five_pV_erg: float,
    four_pV_erg: float,
    extractor_csv: Path | None,
    remote_preflight: dict[str, Any],
    thermal_kinetic_blocker: str,
    gravitational_status: str,
    gravitational_note: str,
) -> dict[str, Any]:
    validate_grid_preflight(remote_preflight)
    comparators = load_comparators(
        level1_path=level1_path,
        level2_path=level2_path,
        pV_erg=pV_erg,
        two_point_five_pV_erg=two_point_five_pV_erg,
        four_pV_erg=four_pV_erg,
    )
    extractor_rows = read_rows(extractor_csv) if extractor_csv else None
    energy_rows = build_energy_rows(
        extractor_rows=extractor_rows,
        comparators=comparators,
        gravitational_status=gravitational_status,
        gravitational_note=gravitational_note,
        thermal_kinetic_blocker=thermal_kinetic_blocker,
    )
    method_rows = method_decision_rows(preflight=remote_preflight, gravitational_status=gravitational_status)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_dict_rows(output_dir / "level3_ambient_energy.csv", energy_rows)
    write_dict_rows(output_dir / "level3_method_decisions.csv", method_rows)
    metadata = {
        "product": "c_hi_final_level3_ambient_energy",
        "date": "2026-06-17",
        "result_status": result_status(energy_rows),
        "comparators_erg": comparators,
        "remote_preflight": remote_preflight,
        "coordinate_compatibility_contract": "enforced_by_extractor_not_remote_preflight",
        "extractor_csv": str(extractor_csv) if extractor_csv else None,
        "tracer_threshold": f"{DEFAULT_TRACER_THRESHOLD:.0e}",
        "thermal_kinetic_blocker": thermal_kinetic_blocker,
        "gravitational_status": gravitational_status,
        "gravitational_note": gravitational_note,
    }
    (output_dir / "level3_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def default_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "level1": repo_root
        / "docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth/level1_injected_energy.csv",
        "level2": repo_root
        / "docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth/level2_tracer_lobe_truth.csv",
        "output": repo_root / "docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17",
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    defaults = default_paths(repo_root)
    parser = argparse.ArgumentParser()
    parser.add_argument("--level1-path", type=Path, default=defaults["level1"])
    parser.add_argument("--level2-path", type=Path, default=defaults["level2"])
    parser.add_argument("--output-dir", type=Path, default=defaults["output"])
    parser.add_argument("--extractor-csv", type=Path)
    args = parser.parse_args()

    metadata = build_package(
        output_dir=args.output_dir,
        level1_path=args.level1_path,
        level2_path=args.level2_path,
        pV_erg=DEFAULT_PV_ERG,
        two_point_five_pV_erg=DEFAULT_TWO_POINT_FIVE_PV_ERG,
        four_pV_erg=DEFAULT_FOUR_PV_ERG,
        extractor_csv=args.extractor_csv,
        remote_preflight=DEFAULT_REMOTE_PREFLIGHT,
        thermal_kinetic_blocker="blocked_remote_postprocessing_access",
        gravitational_status="blocked_missing_potential",
        gravitational_note=(
            "The final and baseline HDF5 outputs expose rho/prs/tr1/vx1/vx2/vx3 but no "
            "gravitational potential. The repo does not contain a reviewed potential/profile "
            "zero-point convention for Level 3 gravitational energy."
        ),
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
