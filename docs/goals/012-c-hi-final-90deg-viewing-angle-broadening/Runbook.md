# Runbook: Goal 012

## Start

```bash
cd /Users/bwbrook/papers/xray_cavities
git fetch --prune origin
git merge --ff-only origin/main
pwd
git status --short --branch
git rev-parse --short HEAD
```

Record these in `Log.md`.

## Target

Produce or submit the final member of the first controlled viewing-angle trio:

```text
case: C-HI
endpoint: final accepted 50 Myr endpoint
accepted baselines: 0 deg and 45 deg
new target: 90 deg final endpoint
scope: one new viewing angle only
```

## Expected Local Paths

Preferred complete-product paths:

```text
docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/
docs/exchange/logs/2026-06-23-c-hi-final-90deg-viewing-angle-broadening.md
docs/goals/012-c-hi-final-90deg-viewing-angle-broadening/Log.md
```

Possible implementation paths, only if needed:

```text
scripts/science/build_final_90deg_viewing_angle_broadening.py
tests/test_final_90deg_viewing_angle_broadening.py
scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
```

## Remote Path Pattern

If full-grid post-processing on Kunanyi is required, use paths like:

```text
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening
```

Use exact paths consistently in logs, wrappers, and retrieval instructions.

## Remote Access Boundary

Use the repo-local helper after the Open OnDemand jumpbox selector is active:

```bash
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd'
```

Do not use Safari for Open OnDemand authentication. If the helper fails because
the jumpbox selector is not active, wake X-ray Cavities and request Chrome or
Computer Use assistance rather than repeatedly probing raw SSH.

## PBS Stop Rule

If a PBS job is submitted:

```bash
qsub <wrapper>
qstat -u "$USER"
```

After verifying the job is queued or running, wake X-ray Cavities with:

- job id;
- job name;
- queue/state;
- requested resources and walltime;
- staged file hashes;
- expected output paths;
- retrieval command sketch.

Then stop. Do not poll for completion.

## Complete-Product Validation

For a complete local package, run the relevant subset:

```bash
uv run pytest <focused new/changed tests> -q
bash -n scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
uv run python -m json.tool <metadata.json>
uv run python - <<'PY'
import csv
from pathlib import Path
for path in Path("docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23").glob("*.csv"):
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise SystemExit(f"{path}: no rows")
    print(f"{path.name}_rows={len(rows)}")
PY
git diff --check
```

Adjust file names to the actual product. Do not run broad suites unless the
changed code justifies them.

## Scientific Guardrails

- Label this as projection-sensitivity work.
- Preserve the connected-envelope/topology caveat.
- Preserve the radio-diagnostic caveat.
- Carry `pV`, `2.5pV`, and `4pV` where cavity-energy quantities are reported.
- Keep gravitational Level 3 as a tracked gap unless separately reviewed.
- Do not claim publication readiness.
- Do not open source-age or comparison-case work.
