import csv
import gzip
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import four_case_energy_partition as partition


def test_public_replay_retains_signed_changes_and_domain_limits(tmp_path):
    result = tmp_path / "replay"
    report = partition.run(result)
    assert (report["retained_snapshots"], report["sphere_rows"], report["fixed_rows"]) == (201, 1206, 1809)
    assert report["checks"]["published_selected_ages"]["count"] == 76
    with (result / "snapshots.csv").open() as stream:
        snapshots = {(r["case"], int(r["snapshot_index"])): r for r in csv.DictReader(stream)}
    with (result / "sphere_components.csv").open() as stream:
        spheres = {(r["case"], int(r["snapshot_index"]), r["aperture"], r["region"]): r for r in csv.DictReader(stream)}
    for case in partition.CASES:
        row = snapshots[case, 0]
        assert float(row["native_lobe_2p5pV_erg"]) > 0
        assert row["native_lobe_2p5pV_over_delivery"] == ""
        for aperture in partition.APERTURES:
            baseline = spheres[case, 0, aperture, "all"]
            assert float(baseline["raw_radius_kpc"]) > 0
            assert baseline["total_over_delivery"] == ""
            assert float(baseline["total_delta_erg"]) == 0
    assert ("G-HI", 48) not in snapshots
    final = spheres["G-HI", 47, "R100", "all"]
    assert final["domain_geometry"] == "domain_truncated_spherical_cell_selection"
    assert final["cocoon_contacts_domain"] == "True"
    assert spheres["G-HI", 46, "R100", "all"]["cocoon_contacts_domain"] == "False"
    outer = spheres["C-LO", 50, "R100", "all"]
    inner = spheres["C-LO", 50, "R300", "all"]
    assert float(outer["total_over_delivery"]) - float(inner["total_over_delivery"]) == pytest.approx(.27401487)
    assert float(spheres["C-LO", 30, "R100", "cocoon"]["total_over_delivery"]) < 0
    assert float(snapshots["C-LO", 30]["cumulative_stationary_gas_delivery_erg"]) < 0


def test_public_replay_rejects_modified_native_basis(tmp_path, monkeypatch):
    with gzip.open(partition.PUBLISHED / partition.BASIS, "rb") as stream:
        source = stream.read()
    (tmp_path / partition.BASIS).write_bytes(gzip.compress(source.rstrip() + b"  \n"))
    monkeypatch.setattr(partition, "PUBLISHED", tmp_path)
    with pytest.raises(ValueError, match="Compact fixed-stock payload differs"):
        partition.run(tmp_path / "result")
    assert not (tmp_path / "result").exists()
