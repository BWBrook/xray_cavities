#!/usr/bin/env python3
"""Build the deterministic Goal 046 lifecycle dependency contracts.

Only compact, committed repository evidence is read.  The resulting files are
an allowlist for the read-only lifecycle inventory; this helper never contacts
Kunanyi and never inspects or changes remote payloads.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


CASES = ("C-HI", "C-LO", "G-LO")
MANIFEST_RELATIVE = (
    "docs/science/assets/three_case_common_age_evolution_2026-07-13/review_products"
)
ROOT_COLUMNS = [
    "case_id",
    "root_id",
    "root_path",
    "root_kind",
    "purpose",
    "expected_presence",
    "source_evidence",
]
PROTECTED_COLUMNS = [
    "path", "protection_class", "dependency", "source_evidence", "existing_sha256",
    "expected_timestep", "expected_time_code", "expected_time_myr",
    "expected_shape", "expected_datasets",
]
HOLD_COLUMNS = ["hold_id", "status", "dependency", "rationale", "source_evidence"]
REMOTE_OUTPUT_RE = re.compile(r"^(?P<root>.+?)/(?P<case>C-(?:HI|LO)|G-LO)/particles/problem/outputs/(?P<name>[^/]+)$")


class ContractError(ValueError):
    """Raised when accepted evidence cannot produce a safe contract."""


def _read_csv(path: Path, required: Iterable[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ContractError(f"missing evidence CSV: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ContractError(f"duplicate CSV header: {path}")
        missing = set(required) - set(fields)
        if missing:
            raise ContractError(f"missing columns {sorted(missing)} in {path}")
        rows = list(reader)
    if not rows:
        raise ContractError(f"empty evidence CSV: {path}")
    return [{key: (value or "").strip() for key, value in row.items()} for row in rows]


def _manifest_rows(repo_root: Path) -> list[tuple[dict[str, str], str]]:
    rows: list[tuple[dict[str, str], str]] = []
    required = ("case", "input_h5", "baseline_h5", "selection_status")
    for case in CASES:
        relative = f"{MANIFEST_RELATIVE}/{case}/compact/source_time_manifest_case.csv"
        path = repo_root / relative
        for row in _read_csv(path, required):
            if row["case"] != case or row["selection_status"] != "selected":
                continue
            rows.append((row, relative))
    if not rows:
        raise ContractError("no selected Goal 041 source rows")
    if {row["case"] for row, _ in rows} != set(CASES):
        raise ContractError("selected Goal 041 sources do not cover all cases")
    return rows


def _output_root(path_string: str, case: str) -> Path:
    path = Path(path_string)
    match = REMOTE_OUTPUT_RE.match(path.as_posix())
    if match and match.group("case") == case:
        return Path(match.group("root")) / case
    # Synthetic fixtures may use a simpler output path; retain only the case
    # directory when one is present, otherwise the parent is the narrowest
    # defensible root supported by the manifest itself.
    parts = path.parts
    if case in parts:
        return Path(*parts[: parts.index(case) + 1])
    return path.parent


def _root_from_path(path_string: str, case: str) -> Path:
    return _output_root(path_string, case)


def _source_evidence_for_manifest(case: str) -> str:
    return f"{MANIFEST_RELATIVE}/{case}/compact/source_time_manifest_case.csv"


def _add_root(
    roots: dict[str, dict[str, str]], *, case_id: str, root_id: str, root_path: Path,
    root_kind: str, purpose: str, expected_presence: str, source_evidence: str,
) -> None:
    row = {
        "case_id": case_id,
        "root_id": root_id,
        "root_path": str(root_path),
        "root_kind": root_kind,
        "purpose": purpose,
        "expected_presence": expected_presence,
        "source_evidence": source_evidence,
    }
    for existing_id, existing in roots.items():
        if existing["root_path"] == row["root_path"]:
            if (existing["case_id"], existing["root_kind"], existing["expected_presence"]) != (
                row["case_id"], row["root_kind"], row["expected_presence"]
            ):
                raise ContractError(f"conflicting root classification: {row['root_path']}")
            return
    previous = roots.get(root_id)
    if previous is not None and previous != row:
        raise ContractError(f"conflicting root classification: {root_id}")
    roots[root_id] = row


def _add_protected(
    rows: dict[str, dict[str, str]], *, path: Path, protection_class: str,
    dependency: str, source_evidence: str, existing_sha256: str = "",
    expected_timestep: str = "", expected_time_code: str = "",
    expected_time_myr: str = "", expected_shape: str = "",
    expected_datasets: str = "",
) -> None:
    row = {
        "path": str(path),
        "protection_class": protection_class,
        "dependency": dependency,
        "source_evidence": source_evidence,
        "existing_sha256": existing_sha256,
        "expected_timestep": expected_timestep,
        "expected_time_code": expected_time_code,
        "expected_time_myr": expected_time_myr,
        "expected_shape": expected_shape,
        "expected_datasets": expected_datasets,
    }
    previous = rows.get(str(path))
    if previous is not None and previous != row:
        raise ContractError(f"conflicting protected classification: {path}")
    rows[str(path)] = row


def _paired_xmf(h5: Path) -> Path:
    if h5.name.endswith(".h5"):
        return h5.with_name(h5.name[:-3] + ".xmf")
    raise ContractError(f"selected source is not HDF5: {h5}")


def _add_source_pair(
    protected: dict[str, dict[str, str]], path_string: str, case: str,
    dependency: str, evidence: str, *, expected_timestep: str = "",
    expected_time_code: str = "", expected_time_myr: str = "",
    expected_shape: str = "", expected_datasets: str = "",
) -> None:
    h5 = Path(path_string)
    _add_protected(
        protected, path=h5, protection_class="KEEP_PROTECTED", dependency=dependency,
        source_evidence=evidence, expected_timestep=expected_timestep,
        expected_time_code=expected_time_code, expected_time_myr=expected_time_myr,
        expected_shape=expected_shape, expected_datasets=expected_datasets,
    )
    _add_protected(
        protected, path=_paired_xmf(h5), protection_class="KEEP_PROTECTED", dependency=dependency,
        source_evidence=evidence,
    )


def _curated_roots(repo_root: Path, roots: dict[str, dict[str, str]]) -> None:
    """Add historical analysis/stage roots only when repo evidence names them."""

    entries = [
        # Historical C-LO continuation roots retained to resolve ownership and
        # any restart links left by the accepted production ladder.
        ("C-LO", "c_lo_initial", "/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO", "production", "Goal 032 initial C-LO production root", "docs/goals/032-c-lo-bounded-execution/Log.md"),
        ("C-LO", "c_lo_continuation1", "/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO", "production", "Goal 033 C-LO continuation root", "docs/goals/033-c-lo-checkpoint-continuation/Log.md"),
        ("C-LO", "c_lo_continuation2", "/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2/C-LO", "production", "Goal 034 C-LO continuation-2 root", "docs/goals/034-c-lo-endpoint-or-continuation-decision/Log.md"),
        # Goal 019/021 late C-HI products.
        ("C-HI", "goal019_analysis", "/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot", "analysis", "Goal 019 late-age analysis", "docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_validation_summary.json"),
        ("ALL", "goal019_stage", "/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot", "stage", "Goal 019 late-age stage", "docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/remote_logs/no_rerun_repackage.stdout.log"),
        ("C-HI", "goal021_analysis", "/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension", "analysis", "Goal 021 late-age analysis", "docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/bounded_age_axis_extension_metadata.json"),
        ("ALL", "goal021_stage", "/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension", "stage", "Goal 021 late-age stage", "docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/product_provenance.csv"),
        # Goal 040 endpoint/truth surface.
        ("ALL", "goal040_analysis", "/scratch/bwbrook/xray_cavities_analysis/2026-07-12-three-case-endpoint-truth-alignment", "analysis", "Goal 040 endpoint/truth analysis", "docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12/remote_logs/three_case_endpoint_truth_alignment.out"),
        ("ALL", "goal040_stage", "/u/bwbrook/codex_kunanyi/goal040_three_case_endpoint_truth_alignment", "stage", "Goal 040 endpoint/truth stage", "docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12/remote_logs/three_case_endpoint_truth_alignment.out"),
        # Goal 044 failed-closed validation and Goal 045 refinement.
        ("ALL", "goal044_analysis", "/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-production-validation", "analysis", "Goal 044 validation analysis", "docs/science/assets/xray_cavity_production_validation_2026-07-23/failed_run/remote_logs/xray_cavity_production_validation.out"),
        ("ALL", "goal044_stage", "/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation", "stage", "Goal 044 validation stage", "docs/science/assets/xray_cavity_production_validation_2026-07-23/failed_run/validation/provenance.csv"),
        ("ALL", "goal045_analysis", "/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-recovery-method-refinement", "analysis", "Goal 045 method-refinement analysis", "docs/science/assets/xray_cavity_recovery_method_refinement_2026-07-23/review_products/validation/input_provenance.csv"),
        ("ALL", "goal045_stage", "/u/bwbrook/codex_kunanyi/goal045_xray_cavity_recovery_method_refinement", "stage", "Goal 045 method-refinement stage", "docs/science/assets/xray_cavity_recovery_method_refinement_2026-07-23/remote_logs/qstat_final.txt"),
    ]
    for case, root_id, root_path, kind, purpose, evidence in entries:
        if (repo_root / evidence).is_file():
            _add_root(
                roots, case_id=case, root_id=root_id, root_path=Path(root_path),
                root_kind=kind, purpose=purpose, expected_presence="optional",
                source_evidence=evidence,
            )


def _goal041_roots(repo_root: Path, roots: dict[str, dict[str, str]]) -> None:
    base = repo_root / "docs/science/assets/three_case_common_age_evolution_2026-07-13"
    for name, filename, kind, purpose in (
        ("goal041_analysis_initial", "pbs_submission.csv", "analysis", "Goal 041 initial analysis roots"),
        ("goal041_analysis_retry1", "pbs_retry_submission.csv", "analysis", "Goal 041 retry analysis roots"),
    ):
        evidence = f"docs/science/assets/three_case_common_age_evolution_2026-07-13/{filename}"
        path = base / filename
        if not path.is_file():
            continue
        for row in _read_csv(path, ("case", "analysis_root")):
            _add_root(
                roots, case_id=row["case"], root_id=f"{name}_{row['case']}",
                root_path=Path(row["analysis_root"]), root_kind=kind,
                purpose=purpose, expected_presence="optional", source_evidence=evidence,
            )
    stage_evidence = "docs/science/assets/three_case_common_age_evolution_2026-07-13/pbs_submission.csv"
    if (repo_root / stage_evidence).is_file():
        _add_root(
            roots, case_id="ALL", root_id="goal041_stage",
            root_path=Path("/u/bwbrook/codex_kunanyi/goal041_three_case_common_age_evolution"),
            root_kind="stage", purpose="Goal 041 stage archives and logs",
            expected_presence="optional", source_evidence=stage_evidence,
        )


def build_contract(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    repo_root = repo_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    manifest_rows = _manifest_rows(repo_root)
    roots: dict[str, dict[str, str]] = {}
    protected: dict[str, dict[str, str]] = {}

    # Selected common-age sources and baselines are the primary required roots.
    for row, evidence in manifest_rows:
        case = row["case"]
        source_root = _root_from_path(row["input_h5"], case)
        base_root = _root_from_path(row["baseline_h5"], case)
        run_labels = {
            "2026-06-01-c-hi-fullgrid-agn-impi-fresh": "c_hi_fresh",
            "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64": "c_hi_prod64",
            "2026-07-05-c-lo-endpoint-oriented-continuation": "c_lo_final",
            "2026-07-07-g-lo-endpoint-oriented-production": "g_lo_production",
            "2026-07-10-g-lo-hdf5-stall-guarded-continuation": "g_lo_guarded",
        }
        source_label = run_labels.get(source_root.parent.name, re.sub(r"[^A-Za-z0-9]+", "_", source_root.parent.name).strip("_"))
        base_label = run_labels.get(base_root.parent.name, re.sub(r"[^A-Za-z0-9]+", "_", base_root.parent.name).strip("_"))
        _add_root(roots, case_id=case, root_id=f"production_{case}_{source_label}", root_path=source_root, root_kind="production", purpose="Goal 041 selected common-age and endpoint sources", expected_presence="required", source_evidence=evidence)
        if base_root != source_root:
            _add_root(roots, case_id=case, root_id=f"production_{case}_{base_label}", root_path=base_root, root_kind="production", purpose="Goal 041 selected baseline source", expected_presence="required", source_evidence=evidence)
        _add_source_pair(
            protected, row["input_h5"], case, "common_age_source", evidence,
            expected_timestep=row["timestep"], expected_time_code=row["time_code"],
            expected_shape=row["grid_shape_nz_ny_nx"],
            expected_datasets="rho;prs;tr1;vx1;vx2;vx3",
        )
        _add_source_pair(
            protected, row["baseline_h5"], case, "baseline_source", evidence,
            expected_timestep=row["baseline_timestep"],
            expected_time_code=row["baseline_time_code"],
            expected_shape=row["baseline_grid_shape_nz_ny_nx"],
            expected_datasets="rho;prs;tr1;vx1;vx2;vx3",
        )

    # Explicit late C-HI float age union on the accepted prod64 root.
    c_hi_endpoint = next(row["input_h5"] for row, _ in manifest_rows if row["case"] == "C-HI" and row["nominal_age_myr"] == "50")
    prod_root = _root_from_path(c_hi_endpoint, "C-HI")
    evidence = "docs/goals/019-c-hi-late-source-age-pilot/Log.md"
    if (repo_root / evidence).is_file():
        for output in (46, 48, 49, 50, 51):
            late_h5 = prod_root / "particles/problem/outputs" / f"data.{output:04d}.flt.h5"
            # Endpoint 51 is already selected by Goal 041; retain its
            # manifest-backed classification rather than creating a duplicate
            # evidence record for the same path.
            if str(late_h5) not in protected:
                _add_source_pair(protected, str(late_h5), "C-HI", "late_age_source", evidence)

    # Restart tuples: retain both XMF sidecars and the explicitly named
    # particle restart.  Other particle payloads are held globally below.
    restart_specs = [
        ("C-HI", "c_hi_fresh", "/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs", "data.0009.dbl.h5", "particles.4277.dbl", "source_restart", "docs/goals/042-three-case-lifecycle-compaction-packet/Goal.md"),
        ("C-HI", "c_hi_prod64", "/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs", "data.0011.dbl.h5", "particles.5000.dbl", "endpoint_preceding_restart", "docs/goals/042-three-case-lifecycle-compaction-packet/Goal.md"),
        ("C-LO", "c_lo_final", "/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles/problem/outputs", "data.0006.dbl.h5", "particles.1611.dbl", "source_restart", "docs/goals/042-three-case-lifecycle-compaction-packet/Goal.md"),
        ("C-LO", "c_lo_final", "/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles/problem/outputs", "data.0013.dbl.h5", "particles.5003.dbl", "endpoint_restart", "docs/goals/042-three-case-lifecycle-compaction-packet/Goal.md"),
        # Goal 038 explicitly identifies the validated source restart as the
        # original Goal 037 path.  The guarded continuation root contains a
        # later restart and must not be substituted for this source tuple.
        ("G-LO", "g_lo_production_source_restart", "/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles/problem/outputs", "data.0002.dbl.h5", "particles.1000.dbl", "source_restart", "docs/goals/038-g-lo-hdf5-stall-guarded-continuation/Log.md", {"expected_timestep": "Timestep_2", "expected_time_code": "3065.934704693023", "expected_shape": "1014x960x960", "expected_datasets": "rho;prs;tr1;vx1;vx2;vx3"}),
        ("G-LO", "g_lo_guarded", "/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs", "data.0009.dbl.h5", "particles.4499.dbl", "preceding_endpoint_restart", "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"),
        ("G-LO", "g_lo_guarded", "/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs", "data.0010.dbl.h5", "particles.5000.dbl", "endpoint_restart", "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"),
    ]
    for spec in restart_specs:
        case, root_id, root_path, h5_name, particle_name, dependency, evidence, *expected = spec
        evidence_path = repo_root / evidence
        if not evidence_path.is_file():
            continue
        _add_root(roots, case_id=case, root_id=root_id, root_path=Path(root_path).parents[2], root_kind="production", purpose="accepted restart and endpoint tuple", expected_presence="required", source_evidence=evidence)
        h5 = Path(root_path) / h5_name
        _add_source_pair(protected, str(h5), case, dependency, evidence, **(expected[0] if expected else {}))
        _add_protected(protected, path=Path(root_path) / particle_name, protection_class="KEEP_PROTECTED", dependency=dependency, source_evidence=evidence)

    _goal041_roots(repo_root, roots)
    _curated_roots(repo_root, roots)

    holds = [
        {"hold_id": "radio_particle_payloads", "status": "active", "dependency": "radio", "rationale": "All particle payloads remain held while radio/raytracing source retention is unresolved.", "source_evidence": "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"},
        {"hold_id": "level3_gravity", "status": "active", "dependency": "level3_gravity", "rationale": "Level 3 gravitational-energy convention remains unresolved; exact baselines/endpoints are protected.", "source_evidence": "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"},
        {"hold_id": "goal044_xray_validation", "status": "retired", "dependency": "xray_validation", "rationale": "Retired by Goal 045 method-refinement resolution; endpoint HDF5 remains protected.", "source_evidence": "docs/science/assets/xray_cavity_recovery_method_refinement_2026-07-23/review_products/contracts/goal045_contract_metadata.json"},
        {"hold_id": "three_case_comparison", "status": "retired", "dependency": "three_case_comparison", "rationale": "Retired after accepted Goal 041 three-case synthesis.", "source_evidence": "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"},
        {"hold_id": "active_production", "status": "retired", "dependency": "active_production", "rationale": "No accepted production job remains an active lifecycle dependency.", "source_evidence": "docs/goals/046-three-case-lifecycle-compaction-authorization/Goal.md"},
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    root_rows = [roots[key] for key in sorted(roots)]
    protected_rows = [protected[key] for key in sorted(protected)]
    hold_rows = sorted(holds, key=lambda row: row["hold_id"])
    _write_csv(output_dir / "remote_root_allowlist.csv", root_rows, ROOT_COLUMNS)
    _write_csv(output_dir / "protected_path_contract.csv", protected_rows, PROTECTED_COLUMNS)
    _write_csv(output_dir / "active_hold_register.csv", hold_rows, HOLD_COLUMNS)
    metadata = {
        "schema_version": "1.0",
        "status": "goal046_contract_ready",
        "goal": "046",
        "cases": list(CASES),
        "source_manifests": [_source_evidence_for_manifest(case) for case in CASES],
        "root_count": len(root_rows),
        "protected_path_count": len(protected_rows),
        "active_hold_count": sum(row["status"] == "active" for row in hold_rows),
        "retired_hold_count": sum(row["status"] == "retired" for row in hold_rows),
        "g_lo_restart_candidates": [
            "source_restart",
            "preceding_endpoint_restart",
            "endpoint_restart",
        ],
        "topology_status": "conditional_general_method_caveat",
        "publication_method_uncertainty_is_raw_data_hold": False,
        "contract_files": ["remote_root_allowlist.csv", "protected_path_contract.csv"],
        "contract_digest_sha256": _digest_outputs(output_dir, ("remote_root_allowlist.csv", "protected_path_contract.csv")),
        "manifest_digest_sha256": _digest_outputs(output_dir, ("remote_root_allowlist.csv", "protected_path_contract.csv")),
    }
    (output_dir / "contract_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def _write_csv(path: Path, rows: Iterable[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _digest_outputs(output_dir: Path, names: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for name in names:
        payload = (output_dir / name).read_bytes()
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    metadata = build_contract(args.repo_root, args.output_dir)
    print(f"goal046_contract={metadata['status']} protected={metadata['protected_path_count']} roots={metadata['root_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
