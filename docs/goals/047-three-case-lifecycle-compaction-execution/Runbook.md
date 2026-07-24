# Runbook: Goal 047

## Frozen Authority

```text
source_commit=1e9866bae48dec72347db1ffa9fa097147d93669
ledger_sha256=df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
delete_hdf5_rows=148
delete_xmf_rows=148
allocated_bytes=6845659111424
```

The executor and wrapper must reject any different values.

## Local Gate

```bash
uv run pytest \
  tests/test_three_case_lifecycle_compaction.py \
  tests/test_three_case_lifecycle_compaction_wrapper.py \
  tests/test_three_case_lifecycle_authorization.py \
  tests/test_three_case_lifecycle_inventory.py -q

uv run python -m py_compile \
  scripts/science/execute_three_case_lifecycle_compaction.py

bash -n scripts/kunanyi/three_case_lifecycle_compaction.pbs
git diff --check
```

## Remote Paths

```text
stage=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction
evidence=/scratch/bwbrook/xray_cavities_analysis/2026-07-24-three-case-lifecycle-compaction-execution
archive=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/three_case_lifecycle_compaction_2026-07-24.tar.gz
stdout=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/three_case_lifecycle_compaction.out
stderr=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/three_case_lifecycle_compaction.err
transcript=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/three_case_lifecycle_compaction_transcript.jsonl
wrapper_failure=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/wrapper_failure_status.json
```

## Pre-Submission Gate

Require:

- all staged hashes match local Git-anchored files;
- a recursive `lstat` gate records zero symlinks anywhere under the staged
  input tree;
- local and remote wrapper syntax pass;
- the ledger hash is the frozen approved digest;
- stage/evidence/archive/reservation targets do not already exist;
- `qstat -u bwbrook` exits zero with no active job rows; and
- the raw qstat transcript records host, UTC time, exact command, exit status,
  and output.

## In-Job Gate

The executor must acquire the compaction lock, allow only `$PBS_JOBID` in the
first qstat check, complete all packet/path/identity/hash checks without
mutation, repeat qstat immediately before deletion, and again allow only
itself. Any other active Barry job fails closed.

The wrapper writes `wrapper_failure_status.json` with no-clobber semantics on
any nonzero shell exit, including a failure before the Python executor starts.
Once the executor starts, its authoritative JSONL transcript and status JSON
record all fail-closed outcomes.

The practical residual assumption is that these Barry-owned roots have no
out-of-band writer not visible to PBS. The executor minimizes that residual by
holding no-follow file descriptors from hash through `unlinkat`.

## Retrieval

After Barry reports the completion email:

```bash
scripts/kunanyi/fetch_from_kunanyi.sh \
  /u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction/three_case_lifecycle_compaction_2026-07-24.tar.gz \
  docs/science/assets/three_case_lifecycle_compaction_execution_2026-07-24/remote_logs/three_case_lifecycle_compaction_2026-07-24.tar.gz
```

Retrieve stdout, stderr, final qstat, and the direct stage-root transcript
separately. Do not retrieve raw HDF5 or particle payloads.
