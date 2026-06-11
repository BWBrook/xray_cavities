# Runbook: Goal 002 Final Sparse PRAiSE Loss Table

## Launch

Start from:

```bash
cd /Users/bwbrook/papers/xray_cavities
pwd
git status --short --branch
git rev-parse --short HEAD
```

Record the output in `Log.md` before editing.

## Read Order

Read:

```text
docs/goals/002-final-sparse-praise-loss-table/Goal.md
docs/goals/002-final-sparse-praise-loss-table/Plan.md
AGENTS.md
docs/exchange/current_status.md
docs/science/sparse_praise_loss_interface_2026-06-11.md
docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md
docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md
docs/science/c_hi_particle_loss_smoke_2026-05-10.md
docs/science/c_hi_particle_radio_smoke_2026-05-10.md
docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md
scripts/science/sparse_particle_radio_bridge.py
scripts/science/xraise_particle_loss_smoke.py
scripts/science/xraise_particle_radio_smoke.py
scripts/science/pluto_particle_sparse_window.py
```

Read existing PBS wrappers as needed; start with:

```text
scripts/kunanyi/c_hi_xraise_particle_loss_smoke.pbs
scripts/kunanyi/c_hi_particle_radio_smoke.pbs
scripts/kunanyi/c_hi_particle_radio_determinism.pbs
scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs
```

## Remote Access

Use the narrowest working Kunanyi route.

Try repo helpers first where appropriate:

```bash
REMOTE_STAGE=/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss
REMOTE_ANALYSIS=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss
scripts/kunanyi/run_on_kunanyi.sh 'hostname; date -u +%Y-%m-%dT%H:%M:%SZ'
scripts/kunanyi/run_on_kunanyi.sh "mkdir -p $REMOTE_STAGE $REMOTE_ANALYSIS"
```

If SSH is blocked by the TPAC jumpbox state, use Chrome or Computer Use to
enable the 5-minute "Enable Jumpbox SSH" selector, then retry the helper route.
Do not use GUI access for broad manual work if terminal helpers are available.

## Required Remote Inputs

Final sparse window:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window
```

Final production PLUTO outputs:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs
```

Existing PRAiSE runtime, if still present:

```text
/u/bwbrook/codex_kunanyi/particle_loss_runtime
```

Use goal-specific staging/output paths to avoid clobbering prior products.

Suggested remote staging root:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss
```

Suggested remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss
```

## Local Validation

Run:

```bash
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Run focused tests for new code. If any PBS wrapper is added or edited, run this
from the repo root and record each checked path:

```bash
for pbs in $(git diff --name-only -- 'scripts/kunanyi/*.pbs'); do
  bash -n "$pbs"
done
```

## Remote Validation Ladder

1. Preflight: confirm required remote paths exist and are readable. Record
   sizes/counts for sparse input files, final particle output, and runtime
   files.
2. Smoke subset: generate a deterministic small selected-ID loss table. Check:
   selected IDs are unique; all expected selected IDs in the subset are
   present; all loss factors are finite and non-negative.
3. Reproducibility: compare `NUMBA_NUM_THREADS=1` against `4` if the smoke
   uses Numba PRAiSE code; otherwise rerun the same smoke command twice. Record
   exact hashes or numeric diffs.
4. Full selected-ID table: generate the final table. Record row count,
   selected-ID coverage, finite/non-negative counts, min/max/mean, and checksum.
5. Bridge: run `sparse_particle_radio_bridge.py --loss-table "$LOSS_TABLE"` and
   confirm metadata reports `external_praise_compatible`.
6. Archive compact outputs and record SHA-256 checksums.

## Hard Stops

Stop immediately before:

- building a dense all-history particle cache;
- changing scientific defaults;
- launching multi-node or long-walltime jobs beyond this bounded table/bridge
  goal;
- editing `/Users/bwbrook/chief_of_staff`;
- editing `/Users/bwbrook/work/goal_composer`;
- editing local UTAS AGN source checkouts;
- committing or pushing.

## Wake-Up Rule

When complete, blocked, or queued/running beyond a sensible monitoring window,
send a short wake-up to the X-ray Cavities orchestrator thread. Include:

- status;
- changed files;
- remote job IDs and outcomes;
- validation result;
- current `git status --short --branch`;
- product locations;
- one-sentence recommendation for the next review step.
