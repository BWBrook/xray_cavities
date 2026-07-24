from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path("scripts/science/build_three_case_lifecycle_contract.py")
REPO = Path(".")
MANIFEST_ROOT = Path(
    "docs/science/assets/three_case_common_age_evolution_2026-07-13/review_products"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_three_case_lifecycle_contract", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(dict.fromkeys(reader.fieldnames or []))
        return list(reader)


def paired_xmf(path: str) -> str:
    return path[:-3] + ".xmf"


def test_real_goal041_common_and_late_age_union_and_restart_tuples(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "one"
    metadata = module.build_contract(REPO, output)
    protected = rows(output / "protected_path_contract.csv")
    protected_by_path = {row["path"]: row for row in protected}

    for case in ("C-HI", "C-LO", "G-LO"):
        manifest = MANIFEST_ROOT / case / "compact/source_time_manifest_case.csv"
        for row in rows(manifest):
            assert row["selection_status"] == "selected"
            assert row["input_h5"] in protected_by_path
            assert paired_xmf(row["input_h5"]) in protected_by_path
            assert row["baseline_h5"] in protected_by_path
            assert paired_xmf(row["baseline_h5"]) in protected_by_path

    c_hi_endpoint = next(
        row["input_h5"]
        for row in rows(MANIFEST_ROOT / "C-HI/compact/source_time_manifest_case.csv")
        if row["nominal_age_myr"] == "50"
    )
    prod64_root = Path(c_hi_endpoint).parent
    for output_index in (46, 48, 49, 50, 51):
        source = str(prod64_root / f"data.{output_index:04d}.flt.h5")
        assert source in protected_by_path
        assert paired_xmf(source) in protected_by_path

    tuples = (
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5",
            "particles.4277.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0011.dbl.h5",
            "particles.5000.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles/problem/outputs/data.0006.dbl.h5",
            "particles.1611.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles/problem/outputs/data.0013.dbl.h5",
            "particles.5003.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles/problem/outputs/data.0002.dbl.h5",
            "particles.1000.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs/data.0009.dbl.h5",
            "particles.4499.dbl",
        ),
        (
            "/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs/data.0010.dbl.h5",
            "particles.5000.dbl",
        ),
    )
    for h5, particle in tuples:
        assert h5 in protected_by_path
        assert paired_xmf(h5) in protected_by_path
        assert str(Path(h5).parent / particle) in protected_by_path

    source_restart = protected_by_path[
        "/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles/problem/outputs/data.0002.dbl.h5"
    ]
    assert source_restart["expected_timestep"] == "Timestep_2"
    assert source_restart["expected_shape"] == "1014x960x960"
    assert source_restart["expected_datasets"] == "rho;prs;tr1;vx1;vx2;vx3"
    assert "/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs/data.0002.dbl.h5" not in protected_by_path

    assert metadata["g_lo_restart_candidates"] == [
        "source_restart",
        "preceding_endpoint_restart",
        "endpoint_restart",
    ]


def test_contract_has_allowed_roots_holds_and_no_duplicate_rows(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "contract"
    module.build_contract(REPO, output)
    roots = rows(output / "remote_root_allowlist.csv")
    protected = rows(output / "protected_path_contract.csv")
    root_paths = [Path(row["root_path"]) for row in roots]
    assert len({row["root_id"] for row in roots}) == len(roots)
    assert all(row["source_evidence"] for row in roots)
    assert len({row["path"] for row in protected}) == len(protected)
    for row in protected:
        path = Path(row["path"])
        assert any(path.is_relative_to(root) for root in root_paths)

    holds = {row["hold_id"]: row for row in rows(output / "active_hold_register.csv")}
    assert holds["radio_particle_payloads"]["status"] == "active"
    assert holds["level3_gravity"]["status"] == "active"
    assert holds["goal044_xray_validation"]["status"] == "retired"
    assert holds["three_case_comparison"]["status"] == "retired"
    assert holds["active_production"]["status"] == "retired"
    assert json.loads((output / "contract_metadata.json").read_text())["publication_method_uncertainty_is_raw_data_hold"] is False


def test_contract_generation_is_byte_identical(tmp_path: Path) -> None:
    module = load_module()
    first = tmp_path / "first"
    second = tmp_path / "second"
    module.build_contract(REPO, first)
    module.build_contract(REPO, second)
    names = (
        "remote_root_allowlist.csv",
        "protected_path_contract.csv",
        "active_hold_register.csv",
        "contract_metadata.json",
    )
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert hashlib.sha256((first / name).read_bytes()).hexdigest()
    metadata = json.loads((first / "contract_metadata.json").read_text())
    digest = hashlib.sha256()
    for name in metadata["contract_files"]:
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update((first / name).read_bytes())
    assert metadata["contract_digest_sha256"] == digest.hexdigest()
