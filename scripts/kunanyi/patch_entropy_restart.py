"""Add a passive RK2 energy-repair ledger to a staged copy of the production PLUTO tree."""

import argparse
import hashlib
import json
from pathlib import Path


SOURCE = {
    "Src/HD/mappers.c": "9a17fbdddf89845c43a5093d40c1133fa04c461b6d266af34a44af5201ccca47",
    "Src/Time_Stepping/rk_step.c": "6104091b37958e762594b331bbd2534b0e2bb1f8eda5736acf140ceb905428dd",
}
HEADER = "entropy_restart_diagnostics.h"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected one exact production source anchor for {old!r}")
    return text.replace(old, new, 1)


def patch_mapper(text: str) -> str:
    include = '#include "pluto.h"\n'
    text = replace_once(text, include, include + f'#include "{HEADER}"\n')
    text = replace_once(
        text, "  double kin, m2, rhog1;\n",
        "  double kin, m2, rhog1;\n"
        "  double audit_e0, audit_after_energy_floor, audit_rho0;\n"
        "  unsigned audit_events;\n",
    )
    text = replace_once(
        text, "    m2  = u[MX1]", "    audit_e0 = audit_after_energy_floor = u[ENG];\n"
        "    audit_rho0 = u[RHO];\n    audit_events = 0;\n\n    m2  = u[MX1]",
    )
    for old, addition in (
        ("      u[RHO]   = g_smallDensity;", "\n      audit_events |= ER_NEG_RHO;"),
        ("      u[ENG]   = g_smallPressure/gmm1 + kin;",
         "\n      audit_after_energy_floor = u[ENG];\n      audit_events |= ER_NEG_E;"),
        ("    if (use_entropy){",
         "\n      audit_events |= ER_USE_S;\n      if (u[ENG] < kin) audit_events |= ER_WOULD_NEG_PE;"),
        ("          Where (i, NULL);\n        )\n        v[PRS]   = g_smallPressure;\n"
         "        flag[i] |= FLAG_CONS2PRIM_FAIL;", "\n        audit_events |= ER_NEG_PS;"),
        ("        u[ENG]   = v[PRS]/gmm1 + kin; /* -- redefine energy -- */",
         "\n        audit_events |= ER_NEG_PE;"),
    ):
        text = replace_once(text, old, old + addition)
    return replace_once(
        text, "    #elif EOS == PVTE_LAW\n\n  /* -- Convert scalars here",
        "    if (EntropyRestartActive) {\n"
        "      EntropyRestartCell(i, flag[i], audit_events, audit_rho0, u[TRC], audit_e0,\n"
        "                         audit_after_energy_floor, u[ENG]);\n    }\n"
        "    #elif EOS == PVTE_LAW\n\n  /* -- Convert scalars here",
    )


def patch_rk(text: str) -> str:
    include = '#include "pluto.h"\n'
    text = replace_once(text, include, include + f'#define ENTROPY_RESTART_IMPLEMENTATION\n#include "{HEADER}"\n')
    call = "  err = ConsToPrim3D (d->Uc, d->Vc, d->flag, &box, grid);\n"
    for stage, prefix in (
        (1, "#ifdef STAGGERED_MHD\n  CT_AverageStaggeredFields (d, 1, &box, grid);\n#endif\n"),
        (2, "/* -- 2f. Convert to Primitive -- */\n\n"),
    ):
        text = replace_once(
            text, prefix + call,
            prefix + f"  EntropyRestartBegin({stage}, grid);\n" + call + "  EntropyRestartActive = NULL;\n",
        )
    success = "  return 0; /* -- step has been achieved, return success -- */"
    return replace_once(text, success, "  EntropyRestartCommit();\n" + success)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pluto-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = args.pluto_dir
    header = Path(__file__).with_name(HEADER).read_bytes()
    header_name = "Src/" + HEADER
    if (root / header_name).exists() or args.receipt.exists():
        raise FileExistsError("use a pristine staged source and a new receipt path")
    changes = {}
    for name, patch in (("Src/HD/mappers.c", patch_mapper), ("Src/Time_Stepping/rk_step.c", patch_rk)):
        original = (root / name).read_bytes()
        if digest(original) != SOURCE[name]:
            raise ValueError(f"production SHA-256 mismatch for {name}")
        changes[name] = patch(original.decode()).encode()
    changes[header_name] = header
    for name, data in changes.items():
        (root / name).write_bytes(data)
    receipt = {
        "original_sha256": SOURCE,
        "staged_sha256": {name: digest(data) for name, data in changes.items()},
        "patcher_sha256": digest(Path(__file__).read_bytes()),
    }
    with args.receipt.open("x") as stream:
        stream.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
