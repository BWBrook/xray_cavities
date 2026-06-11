# Runbook: Goal 003 Final Volume-Coupled Comparison Page

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
docs/goals/003-final-volume-coupled-comparison/Goal.md
docs/goals/003-final-volume-coupled-comparison/Plan.md
AGENTS.md
docs/exchange/current_status.md
docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md
docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md
docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md
scripts/science/sparse_particle_radio_bridge.py
scripts/science/sparse_praise_loss_table.py
scripts/science/pluto_h5_truth_extract.c
scripts/science/build_aligned_smoke_comparison.py
scripts/kunanyi/c_hi_truth_extract.pbs
scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs
```

Read other repo-local files only as needed to implement this packet.

## Remote Access

Use the narrowest working Kunanyi route.

Try repo helpers first where appropriate:

```bash
REMOTE_STAGE=/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison
REMOTE_ANALYSIS=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison
scripts/kunanyi/run_on_kunanyi.sh 'hostname; date -u +%Y-%m-%dT%H:%M:%SZ'
scripts/kunanyi/run_on_kunanyi.sh "mkdir -p $REMOTE_STAGE $REMOTE_ANALYSIS"
```

If SSH is blocked by the TPAC jumpbox state, use Chrome or Computer Use to
enable the 5-minute "Enable Jumpbox SSH" selector, then retry the helper route.
Do not use GUI access for broad manual work if terminal helpers are available.

## Required Remote Inputs

Final HDF5 float output:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
```

Timestep:

```text
Timestep_51
```

Final sparse-window input:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window
```

Goal 002 remote output root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss
```

Goal 002 remote archive:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/full_sparse_praise_loss_2026-06-11.tar.gz
```

Goal 002 local review assets:

```text
docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/
```

Suggested remote staging root:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison
```

Suggested remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison
```

## Local Validation

Run:

```bash
uv run pytest tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Run focused tests for new code. If any PBS wrapper is added or edited, run this
from the repo root and record each checked path:

```bash
for pbs in $(git diff --name-only -- 'scripts/kunanyi/*.pbs'); do
  bash -n "$pbs"
done
```

Before the final wake-up, run:

```bash
git diff --check
```

## Remote Validation Ladder

1. Preflight: confirm required remote paths exist and are readable. Record
   sizes for the final HDF5, Goal 002 loss table or archive, staged scripts,
   and output directories.
2. Truth extraction: compile and run the truth extractor on
   `data.0051.flt.h5` / `Timestep_51`. Record job ID, node, walltime, memory
   if reported, stdout, stderr, file list, and checksums.
3. Truth-table validation: confirm `level2_tracer_lobe_truth.csv` has rows for
   thresholds `1e-3`, `5e-3`, and `1e-2`, and sides `negative_z`,
   `positive_z`, and `bipolar_total`.
4. Volume selection: select the `threshold = 5e-3` rows for `negative_z` and
   `positive_z`. Confirm both `volume_kpc3` values are finite and positive and
   that their sum matches the `bipolar_total` volume within CSV roundoff.
5. Bridge: run:

   ```bash
   SPARSE_WINDOW_DIR=/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window
   FULL_LOSS_TABLE=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/full/sparse_praise_loss_table.csv
   VOLUME_COUPLED_BRIDGE_DIR=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison/bridge_external_loss_volume_coupled
   NEGATIVE_VOLUME_KPC3="$(awk -F, '$1 == "5e-03" && $2 == "negative_z" {print $5}' level2_tracer_lobe_truth.csv)"
   POSITIVE_VOLUME_KPC3="$(awk -F, '$1 == "5e-03" && $2 == "positive_z" {print $5}' level2_tracer_lobe_truth.csv)"

   uv run python scripts/science/sparse_particle_radio_bridge.py \
     --sparse-window-dir "$SPARSE_WINDOW_DIR" \
     --loss-table "$FULL_LOSS_TABLE" \
     --negative-volume-kpc3 "$NEGATIVE_VOLUME_KPC3" \
     --positive-volume-kpc3 "$POSITIVE_VOLUME_KPC3" \
     --output-dir "$VOLUME_COUPLED_BRIDGE_DIR"
   ```

   Adjust interpreter/project flags for the remote environment, but keep the
   bridge inputs equivalent.

6. Bridge validation: confirm metadata reports external PRAiSE-compatible loss,
   zero missing selected IDs, zero extra IDs, and declared side-volume
   assignment. Confirm lobe-summary side volumes match the selected truth
   volumes.
7. Comparison package: build local compact comparison assets from the retrieved
   machine-readable truth and bridge outputs.
8. Archive compact remote products and record SHA-256 checksums.

## Hard Stops

Stop immediately before:

- building a dense all-history particle cache;
- changing scientific defaults;
- changing the Goal 001/002 external loss-table contract;
- launching multi-node or long-walltime jobs beyond this bounded final truth
  and bridge goal;
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
- residual risks and caveats;
- one-sentence recommendation for the next review step.
