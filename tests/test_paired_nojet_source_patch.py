from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "paired_patch", ROOT / "scripts/kunanyi/patch_paired_nojet_sources.py"
)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_patch_transforms_have_exact_single_anchors(tmp_path: Path) -> None:
    rhs = tmp_path / "rhs.c"
    rhs.write_text('#include "pluto.h"\n  TotalFlux(sweep, phi_p, fA, beg-1, end, grid);\n')
    result = PATCH.patched_rhs(rhs, rhs.read_text())
    assert '#include "paired_nojet_diagnostics.h"' in result
    assert result.count("PairedNojetAccumulateBoundaryFlux") == 1

    source = tmp_path / "rhs_source.c"
    blocks = [PATCH.gravity_block(index)[0] for index in "ijk"]
    source.write_text(
        '#include "pluto.h"\n  double r_1, g[3];\n' + "\n".join(blocks)
    )
    result = PATCH.patched_rhs_source(source, source.read_text())
    assert result.count("PairedNojetAccumulateGravityWork") == 3
    assert result.count("paired_nojet_energy_before = rhs[") == 3
    assert result.count("dV[k][j][i]") == 3


def test_inactive_jet_guard_precedes_all_fmod_evaluation(tmp_path: Path) -> None:
    path = tmp_path / "jet.c"
    path.write_text(
        "void f(void) {\n"
        "    int ramp_up, ramp_down;\n\n"
        "    /* Calculate the jet time relative to our start time \n"
        "     * comment */\n"
        "    jet_time = fmod(x, y);\n}\n"
    )
    result = PATCH.patched_jet(path, path.read_text())
    guard = result.index("jip->total_active_time <= 0.0")
    evaluation = result.index("fmod(")
    assert guard < evaluation
    assert "jip->intermittency_velocity_factor = 0.0;" in result
    assert "return;" in result[guard:evaluation]


def test_rk2_conversion_repair_hooks_use_final_solution_weights_and_status(tmp_path: Path) -> None:
    path = tmp_path / "rk_step.c"
    path.write_text(
        '#include "pluto.h"\n'
        "#ifdef STAGGERED_MHD\n"
        "  CT_AverageStaggeredFields (d, 1, &box, grid);\n"
        "#endif\n"
        "  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);\n"
        "/* -- 2f. Convert to Primitive -- */\n\n"
        "  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);\n"
    )
    result = PATCH.patched_rk_step(path, path.read_text())
    assert result.count("PairedNojetBeginConversionEnergyRepair(0.5, grid)") == 1
    assert result.count("PairedNojetBeginConversionEnergyRepair(1.0, grid)") == 1
    assert result.count("PairedNojetEndConversionEnergyRepair(err)") == 2


def test_hd_mapper_records_cell_energy_mutation_without_an_extra_grid_scan(tmp_path: Path) -> None:
    path = tmp_path / "mappers.c"
    path.write_text(
        '#include "pluto.h"\n'
        "  double kin, m2, rhog1;\n"
        "    u = ucons[i];\n    v = uprim[i];\n"
        "    #endif\n  }\n  return ifail;\n}\n"
    )
    result = PATCH.patched_hd_mappers(path, path.read_text())
    assert result.count("paired_nojet_energy_before = u[ENG]") == 1
    assert result.count("PairedNojetRecordConversionEnergyRepairCell") == 1
    assert "u[ENG] - paired_nojet_energy_before, i, flag[i]" in result


def test_conversion_diagnostics_expose_cellwise_gross_and_failure_evidence() -> None:
    source = (ROOT / "scripts/kunanyi/paired_nojet_diagnostics.c").read_text()
    assert "entropy_energy_repair" not in source
    for column in (
        "conversion_energy_repair_net_interval_erg",
        "conversion_energy_repair_positive_interval_erg",
        "conversion_energy_repair_negative_interval_erg",
        "conversion_energy_repair_gross_interval_erg",
        "conversion_energy_repair_net_cumulative_erg",
        "conversion_energy_repair_positive_cumulative_erg",
        "conversion_energy_repair_negative_cumulative_erg",
        "conversion_energy_repair_gross_cumulative_erg",
        "conversion_failure_flagged_cell_observations_interval_count",
        "conversion_failure_flagged_cell_observations_cumulative_count",
        "conversion_nonzero_return_call_interval_count",
        "conversion_nonzero_return_call_cumulative_count",
    ):
        assert source.count(column) == 1
    assert "add_signed(weighted_change, step_conversion_energy_repair);" in source
    assert "step_conversion_energy_repair_gross += fabs(weighted_change);" in source
    assert "if (flag & FLAG_CONS2PRIM_FAIL)" in source
    assert "if (conversion_status != 0) step_conversion_nonzero_return_calls++;" in source
    assert "1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD" in source
    assert "1, MPI_LONG, MPI_MAX, 0, MPI_COMM_WORLD" in source


def test_local_make_drops_particle_objects_and_adds_only_diagnostics(tmp_path: Path) -> None:
    path = tmp_path / "local_make"
    path.write_text(
        "include Particles/makefile\n\n"
        "OBJ += coordinates.o jet.o units.o environment_utilities.o environment.o tools_usr.o read_external_pressure.o galaxy.o\n"
        "HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h units.h environment_utilities.h environment.h tools_usr.h read_external_pressure.h galaxy.h\n"
    )
    result = PATCH.patched_local_make(path, path.read_text())
    assert "Particles/makefile" not in result
    assert result.count("paired_nojet_diagnostics.o") == 1
    assert result.count("paired_nojet_diagnostics.h") == 1


def test_init_requires_explicit_staged_atmosphere_and_installs_analysis_hook(tmp_path: Path) -> None:
    path = tmp_path / "init.c"
    path.write_text(
        '#include "tools_usr.h"\n'
        '      set_tabulated_env_path(&ep, "./data/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv");\n'
        "void Analysis (const Data *d, Grid *grid)\n/* \n *\n **************************************************************** */\n{ }\n"
    )
    result = PATCH.patched_init(path, path.read_text())
    assert result.count("getenv(\"PAIRED_NOJET_TABLE\")") == 1
    assert "set_tabulated_env_path(&ep, paired_nojet_table);" in result
    assert "PairedNojetAnalysis(d, grid);" in result
    assert "PLUTO_data_best" not in result


def test_raw_input_alias_is_conditional_and_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "menu.py"
    original = "import os, sys, traceback, time, string\n"
    patched, action = PATCH.patched_menu(path, original)
    assert action == "added"
    assert patched == original + "raw_input = input\n"
    same, action = PATCH.patched_menu(path, patched)
    assert action == "already_present"
    assert same == patched
    with pytest.raises(RuntimeError, match="exactly one patch anchor"):
        PATCH.patched_menu(path, "import os\n")


def test_stage_receipt_binds_guarded_preimages_and_outputs() -> None:
    receipt_path = ROOT / "source_patch_receipt.json"
    if not receipt_path.is_file():
        pytest.skip("source patch receipt exists only in the exported Kunanyi stage")
    receipt = json.loads(receipt_path.read_text())
    assert receipt["schema_version"] == 1
    assert receipt["status"] == "verified"
    assert len(receipt["source_guards"]) == len(PATCH.SOURCE_GUARDS)
    guards = {(row["tree"], row["path"]): row for row in receipt["source_guards"]}
    modified = {(row["tree"], row["path"]): row for row in receipt["modified_files"]}
    staged_roots = {
        "pluto": ROOT / "source/pluto",
        "jet-setup": ROOT / "source/jet-setup",
    }
    for key, expected in PATCH.SOURCE_GUARDS.items():
        assert guards[key]["expected_sha256"] == expected
        assert guards[key]["observed_sha256"] == expected
        assert modified[key]["before_sha256"] == expected
        assert digest(staged_roots[key[0]] / key[1]) == modified[key]["after_sha256"]
    for row in receipt["new_files"]:
        assert row["source_sha256"] == row["after_sha256"]
        assert digest(staged_roots[row["tree"]] / row["path"]) == row["after_sha256"]
