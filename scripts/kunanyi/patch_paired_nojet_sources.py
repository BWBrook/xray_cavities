#!/usr/bin/env python3
"""Patch pristine PLUTO and jet-setup snapshots for paired no-jet diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Final


SOURCE_GUARDS: Final = {
    ("pluto", "Src/MHD/rhs.c"): "398607236523f2d5f59eeb68cd53f5f66749b029c0774fa0bef3ad8a8d9cee35",
    ("pluto", "Src/MHD/rhs_source.c"): "3a81c865e314a5691ef4585a06c71f0ca6de5867d09c67e6cf97bdd84ad72c29",
    ("pluto", "Src/HD/mappers.c"): "9a17fbdddf89845c43a5093d40c1133fa04c461b6d266af34a44af5201ccca47",
    ("pluto", "Src/Time_Stepping/rk_step.c"): "6104091b37958e762594b331bbd2534b0e2bb1f8eda5736acf140ceb905428dd",
    ("pluto", "Tools/Python/menu.py"): "50527a6dfbc56ea739dd6e5188cce066c323abe76c7304ba9b3de16c9fb8f945",
    ("jet-setup", "src/init.c"): "320100a6d68c2e58858ac34278bf232570b7596932f0a815156340a19cea11d6",
    ("jet-setup", "src/jet.c"): "ff1e18451c19c80cd408e25d4ec5d15a19d6f4d78d9d49a5466186bb884ac7e4",
    ("jet-setup", "src/local_make"): "a6d48e8063697efc23265e45ed576adcbece0039175647abb3287af8a09f269d",
}

DIAGNOSTIC_FILES: Final = ("paired_nojet_diagnostics.c", "paired_nojet_diagnostics.h")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text: str, old: str, new: str, path: Path) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one patch anchor, found {count}")
    return text.replace(old, new, 1)


def patched_rhs(path: Path, text: str) -> str:
    text = replace_once(
        text,
        '#include "pluto.h"\n',
        '#include "pluto.h"\n#include "paired_nojet_diagnostics.h"\n',
        path,
    )
    return replace_once(
        text,
        "  TotalFlux(sweep, phi_p, fA, beg-1, end, grid);\n",
        "  TotalFlux(sweep, phi_p, fA, beg-1, end, grid);\n"
        "  PairedNojetAccumulateBoundaryFlux(sweep, beg, end, dt, grid);\n",
        path,
    )


def gravity_block(index: str) -> tuple[str, str]:
    if index == "i":
        old = ("""      #if (BODY_FORCE & VECTOR)
      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);
      rhs[i][MX1]   += dt*vg[RHO]*g[IDIR];
      IF_DUST_FLUID(rhs[i][MX1_D] += dt*vg[RHO_D]*g[IDIR];)
      IF_ENERGY(    rhs[i][ENG]   += dt*0.5*(flux[i][RHO] + flux[i-1][RHO])*g[IDIR];)
""" + "      \n" + """      /* ----------------------------------------
         Add non-active dimensions during
         this sweep.
         ---------------------------------------- */
      #if !INCLUDE_JDIR && !INCLUDE_KDIR
      rhs[i][MX2] += dt*vg[RHO]*g[JDIR];
      IF_DUST_FLUID(rhs[i][MX2_D] += dt*vg[RHO_D]*g[JDIR];)
      IF_ENERGY    (rhs[i][ENG]   += dt*vg[RHO]*vg[VX2]*g[JDIR];)

      rhs[i][MX3] += dt*vg[RHO]*g[KDIR];
      IF_DUST_FLUID(rhs[i][MX3_D] += dt*vg[RHO_D]*g[KDIR];)
      IF_ENERGY    (rhs[i][ENG]   += dt*vg[RHO]*vg[VX3]*g[KDIR];)
      #endif
      #endif
""")
        new = old.replace(
            "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
            "      IF_ENERGY(paired_nojet_energy_before = rhs[i][ENG];)\n"
            "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
            1,
        ).replace(
            "      #endif\n      #endif\n",
            "      #endif\n"
            "      IF_ENERGY(PairedNojetAccumulateGravityWork(\n"
            "          rhs[i][ENG] - paired_nojet_energy_before, dV[k][j][i]);)\n"
            "      #endif\n",
            1,
        )
        return old, new
    if index == "j":
        old = """      #if (BODY_FORCE & VECTOR)
      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);
      rhs[j][MX2] += dt*vg[RHO]*g[JDIR];
      IF_DUST_FLUID(rhs[j][MX2_D]  += dt*vg[RHO_D]*g[JDIR]);
      IF_ENERGY(rhs[j][ENG] += dt*0.5*(flux[j][RHO] + flux[j-1][RHO])*g[JDIR];)
      #if !INCLUDE_KDIR
      rhs[j][MX3] += dt*vg[RHO]*g[KDIR];
      IF_DUST_FLUID(rhs[j][MX3_D] += dt*vg[RHO_D]*g[KDIR];)
      IF_ENERGY    (rhs[j][ENG]   += dt*vg[RHO]*vg[VX3]*g[KDIR];)
      #endif
      #endif /* (BODY_FORCE & VECTOR) */
"""
        new = old.replace(
            "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
            "      IF_ENERGY(paired_nojet_energy_before = rhs[j][ENG];)\n"
            "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
            1,
        ).replace(
            "      #endif /* (BODY_FORCE & VECTOR) */\n",
            "      IF_ENERGY(PairedNojetAccumulateGravityWork(\n"
            "          rhs[j][ENG] - paired_nojet_energy_before, dV[k][j][i]);)\n"
            "      #endif /* (BODY_FORCE & VECTOR) */\n",
            1,
        )
        return old, new
    old = """      #if (BODY_FORCE & VECTOR)
      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);
      rhs[k][MX3] += dt*vg[RHO]*g[KDIR];
      IF_DUST_FLUID(rhs[k][MX3_D] += dt*vg[RHO_D]*g[KDIR];)
      IF_ENERGY(rhs[k][ENG] += dt*0.5*(flux[k][RHO] + flux[k-1][RHO])*g[KDIR];)
      #if !INCLUDE_JDIR
      rhs[k][MX2] += dt*vg[RHO]*g[JDIR];
      IF_DUST_FLUID(rhs[k][MX2_D] += dt*vg[RHO_D]*g[JDIR];)
      IF_ENERGY    (rhs[k][ENG]   += dt*vg[RHO]*vg[VX2]*g[JDIR];)
      #endif
      #endif  /* (BODY_FORCE & VECTOR) */
"""
    new = old.replace(
        "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
        "      IF_ENERGY(paired_nojet_energy_before = rhs[k][ENG];)\n"
        "      BodyForceVector(vg, g, x1[i], x2[j], x3[k]);\n",
        1,
    ).replace(
        "      #endif  /* (BODY_FORCE & VECTOR) */\n",
        "      IF_ENERGY(PairedNojetAccumulateGravityWork(\n"
        "          rhs[k][ENG] - paired_nojet_energy_before, dV[k][j][i]);)\n"
        "      #endif  /* (BODY_FORCE & VECTOR) */\n",
        1,
    )
    return old, new


def patched_rhs_source(path: Path, text: str) -> str:
    text = replace_once(
        text,
        '#include "pluto.h"\n',
        '#include "pluto.h"\n#include "paired_nojet_diagnostics.h"\n',
        path,
    )
    text = replace_once(
        text,
        "  double r_1, g[3];\n",
        "  double r_1, g[3];\n  double paired_nojet_energy_before = 0.0;\n",
        path,
    )
    for index in "ijk":
        old, new = gravity_block(index)
        text = replace_once(text, old, new, path)
    return text


def patched_rk_step(path: Path, text: str) -> str:
    text = replace_once(
        text,
        '#include "pluto.h"\n',
        '#include "pluto.h"\n#include "paired_nojet_diagnostics.h"\n',
        path,
    )
    predictor = """#ifdef STAGGERED_MHD
  CT_AverageStaggeredFields (d, 1, &box, grid);
#endif
  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);
"""
    text = replace_once(
        text,
        predictor,
        """#ifdef STAGGERED_MHD
  CT_AverageStaggeredFields (d, 1, &box, grid);
#endif
  PairedNojetBeginConversionEnergyRepair(0.5, grid);
  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);
  PairedNojetEndConversionEnergyRepair(err);
""",
        path,
    )
    corrector = """/* -- 2f. Convert to Primitive -- */

  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);
"""
    return replace_once(
        text,
        corrector,
        """/* -- 2f. Convert to Primitive -- */

  PairedNojetBeginConversionEnergyRepair(1.0, grid);
  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);
  PairedNojetEndConversionEnergyRepair(err);
""",
        path,
    )


def patched_hd_mappers(path: Path, text: str) -> str:
    text = replace_once(
        text,
        '#include "pluto.h"\n',
        '#include "pluto.h"\n#include "paired_nojet_diagnostics.h"\n',
        path,
    )
    text = replace_once(
        text,
        "  double kin, m2, rhog1;\n",
        "  double kin, m2, rhog1;\n  double paired_nojet_energy_before;\n",
        path,
    )
    text = replace_once(
        text,
        "    u = ucons[i];\n    v = uprim[i];\n",
        "    u = ucons[i];\n    v = uprim[i];\n    paired_nojet_energy_before = u[ENG];\n",
        path,
    )
    return replace_once(
        text,
        "    #endif\n  }\n  return ifail;\n}",
        "    #endif\n"
        "    PairedNojetRecordConversionEnergyRepairCell(\n"
        "        u[ENG] - paired_nojet_energy_before, i, flag[i]);\n"
        "  }\n  return ifail;\n}",
        path,
    )


def patched_init(path: Path, text: str) -> str:
    text = replace_once(
        text,
        '#include "tools_usr.h"\n',
        '#include "tools_usr.h"\n#include "paired_nojet_diagnostics.h"\n',
        path,
    )
    text = replace_once(
        text,
        "void Analysis (const Data *d, Grid *grid)\n/* \n *\n **************************************************************** */\n{ }",
        "void Analysis (const Data *d, Grid *grid)\n/* \n *\n **************************************************************** */\n"
        "{\n  PairedNojetAnalysis(d, grid);\n}",
        path,
    )
    return replace_once(
        text,
        '      set_tabulated_env_path(&ep, "./data/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv");\n',
        "      const char *paired_nojet_table = getenv(\"PAIRED_NOJET_TABLE\");\n"
        "      if (paired_nojet_table == NULL || paired_nojet_table[0] == '\\0') {\n"
        "        print(\"PAIRED_NOJET_TABLE must name the staged atmosphere table\\n\");\n"
        "        QUIT_PLUTO(1);\n"
        "      }\n"
        "      set_tabulated_env_path(&ep, paired_nojet_table);\n",
        path,
    )


def patched_jet(path: Path, text: str) -> str:
    return replace_once(
        text,
        """    int ramp_up, ramp_down;

""" + "    /* Calculate the jet time relative to our start time \n",
        """    int ramp_up, ramp_down;

    if (jip->total_active_time <= 0.0 || jip->duty_cycle_time <= 0.0) {
        jip->is_active = 0;
        jip->intermittency_velocity_factor = 0.0;
        jip->have_set_timestep = 0;
        return;
    }

""" + "    /* Calculate the jet time relative to our start time \n",
        path,
    )


def patched_local_make(path: Path, text: str) -> str:
    text = replace_once(
        text,
        "include Particles/makefile\n\nOBJ += coordinates.o jet.o units.o environment_utilities.o environment.o tools_usr.o read_external_pressure.o galaxy.o\n",
        "OBJ += coordinates.o jet.o units.o environment_utilities.o environment.o tools_usr.o read_external_pressure.o galaxy.o paired_nojet_diagnostics.o\n",
        path,
    )
    return replace_once(
        text,
        "HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h units.h environment_utilities.h environment.h tools_usr.h read_external_pressure.h galaxy.h\n",
        "HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h units.h environment_utilities.h environment.h tools_usr.h read_external_pressure.h galaxy.h paired_nojet_diagnostics.h\n",
        path,
    )


def patched_menu(path: Path, text: str) -> tuple[str, str]:
    if "raw_input = input" in text:
        return text, "already_present"
    patched = replace_once(
        text,
        "import os, sys, traceback, time, string\n",
        "import os, sys, traceback, time, string\nraw_input = input\n",
        path,
    )
    return patched, "added"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pluto-dir", type=Path, required=True)
    parser.add_argument("--jet-setup-dir", type=Path, required=True)
    parser.add_argument("--diagnostics-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = {"pluto": args.pluto_dir.resolve(), "jet-setup": args.jet_setup_dir.resolve()}
    diagnostics_dir = args.diagnostics_dir.resolve()
    receipt_path = args.receipt.resolve()
    if receipt_path.exists():
        raise FileExistsError(f"refusing to replace existing receipt: {receipt_path}")

    guards = []
    originals: dict[tuple[str, str], str] = {}
    for (tree, relative), expected in SOURCE_GUARDS.items():
        path = roots[tree] / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        guards.append(
            {
                "tree": tree,
                "path": relative,
                "expected_sha256": expected,
                "observed_sha256": observed,
            }
        )
        if observed != expected:
            raise RuntimeError(
                f"source guard failed for {tree}/{relative}: expected {expected}, observed {observed}"
            )
        originals[(tree, relative)] = path.read_text(encoding="utf-8")

    diagnostic_sources = []
    for name in DIAGNOSTIC_FILES:
        source = diagnostics_dir / name
        if not source.is_file():
            raise FileNotFoundError(source)
        diagnostic_sources.append({"path": name, "sha256": sha256(source)})

    patched: dict[tuple[str, str], str] = {}
    patched[("pluto", "Src/MHD/rhs.c")] = patched_rhs(
        roots["pluto"] / "Src/MHD/rhs.c", originals[("pluto", "Src/MHD/rhs.c")]
    )
    patched[("pluto", "Src/MHD/rhs_source.c")] = patched_rhs_source(
        roots["pluto"] / "Src/MHD/rhs_source.c",
        originals[("pluto", "Src/MHD/rhs_source.c")],
    )
    patched[("pluto", "Src/Time_Stepping/rk_step.c")] = patched_rk_step(
        roots["pluto"] / "Src/Time_Stepping/rk_step.c",
        originals[("pluto", "Src/Time_Stepping/rk_step.c")],
    )
    patched[("pluto", "Src/HD/mappers.c")] = patched_hd_mappers(
        roots["pluto"] / "Src/HD/mappers.c",
        originals[("pluto", "Src/HD/mappers.c")],
    )
    menu, raw_input_action = patched_menu(
        roots["pluto"] / "Tools/Python/menu.py",
        originals[("pluto", "Tools/Python/menu.py")],
    )
    patched[("pluto", "Tools/Python/menu.py")] = menu
    patched[("jet-setup", "src/init.c")] = patched_init(
        roots["jet-setup"] / "src/init.c", originals[("jet-setup", "src/init.c")]
    )
    patched[("jet-setup", "src/jet.c")] = patched_jet(
        roots["jet-setup"] / "src/jet.c", originals[("jet-setup", "src/jet.c")]
    )
    patched[("jet-setup", "src/local_make")] = patched_local_make(
        roots["jet-setup"] / "src/local_make", originals[("jet-setup", "src/local_make")]
    )

    new_destinations = [roots["jet-setup"] / "src" / name for name in DIAGNOSTIC_FILES]
    for destination in new_destinations:
        if destination.exists():
            raise FileExistsError(f"refusing to replace diagnostic source: {destination}")

    modified_files = []
    for (tree, relative), content in patched.items():
        path = roots[tree] / relative
        before = sha256(path)
        path.write_text(content, encoding="utf-8")
        modified_files.append(
            {
                "tree": tree,
                "path": relative,
                "before_sha256": before,
                "after_sha256": sha256(path),
            }
        )

    new_files = []
    for name in DIAGNOSTIC_FILES:
        source = diagnostics_dir / name
        destination = roots["jet-setup"] / "src" / name
        shutil.copyfile(source, destination)
        source_hash = sha256(source)
        destination_hash = sha256(destination)
        if source_hash != destination_hash:
            raise RuntimeError(f"copied diagnostic source hash mismatch: {name}")
        new_files.append(
            {
                "tree": "jet-setup",
                "path": f"src/{name}",
                "source_path": str(source),
                "source_sha256": source_hash,
                "after_sha256": destination_hash,
            }
        )

    receipt = {
        "schema_version": 1,
        "status": "verified",
        "roots": {tree: str(root) for tree, root in roots.items()},
        "diagnostics_dir": str(diagnostics_dir),
        "source_guards": guards,
        "modified_files": modified_files,
        "new_files": new_files,
        "diagnostic_sources": diagnostic_sources,
        "raw_input_alias": raw_input_action,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
