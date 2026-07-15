# Goal 041 Log - Three-case common-age evolution

## Objective

Build the common `10/20/30/40/50 Myr`, `0/45/90 deg` C-HI/C-LO/G-LO
evolution surface from accepted production outputs, including XRAiSE recovery,
Level 1/2 truth, cavity energetics, and Level 3 thermal plus kinetic ambient
energy, without another PLUTO run.

## Method development

The implementation adds:

- `scripts/science/select_common_age_hdf5.py` for HDF5-Time-based common-age
  selection across promoted run segments;
- `scripts/science/validate_common_age_endpoint_reuse.py` for hash-locked Goal
  040 endpoint reuse;
- `scripts/science/build_goal041_scratch_gate.py` for fail-closed capacity and
  lifecycle validation;
- `scripts/science/analyse_common_age_case.py` for per-case compact synthesis;
- time-aware reuse of the accepted Goal 040 recovery engine;
- `scripts/kunanyi/three_case_common_age_evolution.pbs` for one independent
  case job.

The local implementation validates generated truth, cavity, Level 3, and
XRAiSE times against the selected HDF5 manifest. It requires the complete Goal
040 physical-area method and sensitivity grid, and carries a dependency ledger
for raw sources and processed arrays.

## Independent worker evidence

A read-only `luna_light_scout` inventory was accepted only after root
verification. A bounded `luna_high_executor` implementation run hit its
900-second hard timeout and was not retried; root inspected and repaired its
partial implementation. A read-only `sol_medium_scientist` review identified
three material gates: exact zero-time baselines, explicit endpoint time/method
binding, and scratch/lifecycle control. Root implemented all three and reran
the complete acceptance suite.

## Local validation

Final pre-staging validation:

```text
uv run pytest tests/test_select_common_age_hdf5.py \
  tests/test_analyse_common_age_case.py \
  tests/test_validate_common_age_endpoint_reuse.py \
  tests/test_goal041_scratch_gate.py \
  tests/test_three_case_common_age_evolution_wrapper.py \
  tests/test_build_three_case_cavity_recovery.py \
  tests/test_three_case_cavity_recovery.py \
  tests/test_build_three_case_truth_alignment.py \
  tests/test_three_case_endpoint_truth_alignment_wrapper.py \
  tests/test_pluto_h5_level3_ambient_extract.py \
  tests/test_final_level3_remote_extraction_closeout.py \
  tests/test_xraise_grid_smoke_projection.py -q
46 passed in 1.14s

bash -n scripts/kunanyi/three_case_common_age_evolution.pbs
passed

git diff --check
passed
```

The endpoint reuse validator produced nine locked case/view rows and passed
the accepted Goal 040 hash, method, time, projection, sensitivity, truth, and
shell-context checks.

## Remote source and storage gate

Chrome/Open OnDemand refreshed the TPAC selector; all subsequent work used the
repo-local terminal helpers.

Retained float-HDF5 chains:

- C-HI: outputs `0-43` in the fresh run and `44-51` in the final run;
- C-LO: consolidated outputs `0-53` in the endpoint run;
- G-LO: outputs `0-14` in the original run and `11-50` in the guarded
  continuation.

The selector found exactly one requested age per case within `0.05 Myr`. All
three zero-time baselines have `Time=0`, required datasets, and shape
`1014 x 960 x 960`.

The live scratch write probe passed. Available space was
`3,204,297,185,558,528` bytes. The three-case forecast is
`3,434,141,724` bytes before and `4,120,970,069` bytes after the 20 percent
safety factor; headroom ratio is `777558.9562425739`.

## Staging and remote validation

Stage root:

`/u/bwbrook/codex_kunanyi/goal041_three_case_common_age_evolution`

All 20 staged and shared dependencies matched
`staged_hash_manifest.sha256`. Remote wrapper syntax passed. The Anaconda
runtime compiled every staged Python module and parsed the source, endpoint,
and scratch contracts. `HDF5/1.14.0-gompi-2023a` loaded and `h5pcc` resolved.
All analysis and archive targets were absent. The `normal` queue was enabled
and started.

## Submission

Exactly three independent post-processing jobs were submitted:

```text
757145.kunanyi-ohpc  c_hi_ageev  R  normal
757146.kunanyi-ohpc  c_lo_ageev  Q  normal
757147.kunanyi-ohpc  g_lo_ageev  Q  normal
```

Each requests `select=1:ncpus=1:mpiprocs=1:mem=96gb` and
`walltime=12:00:00`.

Expected archives:

- `three_case_common_age_evolution_c_hi_2026-07-13.tar.gz`;
- `three_case_common_age_evolution_c_lo_2026-07-13.tar.gz`;
- `three_case_common_age_evolution_g_lo_2026-07-13.tar.gz`.

All are under the stage root. Combined case logs use
`{c_hi,c_lo,g_lo}_common_age_evolution.out`.

## 2026-07-14 Failure Check And Runtime Repair

Barry explicitly authorized a live scheduler re-check after more than 30 hours
without completion email. All three original jobs had entered PBS and started,
but finished almost immediately with `Exit_status=1`:

```text
757145.kunanyi-ohpc  c_hi_ageev  F  00:00:08
757146.kunanyi-ohpc  c_lo_ageev  F  00:00:12
757147.kunanyi-ohpc  g_lo_ageev  F  00:00:12
```

Each passed the manifest, endpoint, and scratch gates. Each then failed at the
first truth-extractor invocation because `libsz.so.2` was unavailable after a
module purge. The wrapper now retains the HDF5 dependency environment while
adding Anaconda and validates both compiled extractors with `ldd` before
analysis. Local focused tests passed (`18 passed`), wrapper syntax passed, and
the remote combined Python/HDF5 plus all-six-binary linkage preflight passed.

The repaired wrapper and hash manifest were restaged. New roots and archives
were used, leaving the failed attempt untouched. Retry jobs at the stop gate:

```text
770758.kunanyi-ohpc  c_hi_ageev_r1  Q  normal
770759.kunanyi-ohpc  c_lo_ageev_r1  Q  normal
770760.kunanyi-ohpc  g_lo_ageev_r1  Q  normal
```

## 2026-07-15 Retry Completion And Retrieval

Barry explicitly authorized a live sanity check after no completion emails
arrived. All three repaired retries had started immediately and completed
successfully:

```text
770758.kunanyi-ohpc  c_hi_ageev_r1  F  Exit_status=0  02:16:43
770759.kunanyi-ohpc  c_lo_ageev_r1  F  Exit_status=0  02:22:12
770760.kunanyi-ohpc  g_lo_ageev_r1  F  Exit_status=0  02:22:59
```

Every scheduler record has `Stageout_status=1`. The stage-root compact
archives and logs were nevertheless present. All three stderr files are empty,
all archives pass `tar -tzf`, and every compact product passes its internal
SHA-256 manifest. The extracted case metadata status is
`complete_case_product_pending_endpoint_merge` for C-HI, C-LO, and G-LO.

The missing completion emails are therefore an operational notification issue,
not evidence that these jobs failed. The exact relationship between the email
absence and `Stageout_status=1` remains unproven.

At this retrieval checkpoint, all three case products were complete and ready
for the local endpoint merge. The final Goal 041 status is recorded below.

## 2026-07-15 Local Endpoint Merge And Synthesis

A read-only `sol_medium_scientist` design review ran through the approved
`codex-profile-exec` route with minimal context. Persisted runner metadata
confirmed `gpt-5.6-sol`, medium reasoning, recursive multi-agent disabled,
return code 0, and no worker mutation. Root independently verified its central
finding against the frozen three-case specification, Meeting 2 action plan,
production wrappers, accepted Goal 040 Level 1 source, and returned Goal 041
tables.

The review exposed a material Goal 041 packaging error: every returned C-HI
source-manifest row declared `1e44 erg/s`, while the authoritative one-sided
C-HI power is `1e45 erg/s`. This caused the 10-40 Myr C-HI Level 1 energies to
be low by a factor of ten and inflated dependent ratios. C-LO and G-LO power
bindings were correct.

The repair is local and definition preserving:

- original retrieved compact products remain unchanged;
- `correction_register.csv` records the authority, affected fields, and scope;
- C-HI Level 1 values are recomputed from `2 * P_one-sided * actual_time`;
- only Level 1-dependent hybrid and truth ratios are recalculated;
- Level 2, Level 3, X-ray, geometry, pressure, and shell-age values are not
  changed;
- the accepted Goal 040 endpoint remains the 50 Myr authority;
- `analyse_common_age_case.py` and the PBS wrapper now reject future
  case-power drift before analysis.

New local builder and tests:

- `scripts/science/build_three_case_common_age_synthesis.py`;
- `tests/test_three_case_common_age_synthesis.py`.

The synthesis output is:

`docs/science/assets/three_case_common_age_evolution_2026-07-13/synthesis/`

It contains 15 truth rows, 45 observer rows, 963 hybrid rows, 45 sensitivity
summaries, 20 descriptive contrasts, one correction register, nine validation
gates, two figures, metadata, and a SHA-256 manifest.

## Final Status

`complete_local_synthesis`

Decision label:
`THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE`.

No further remote compute is required for Goal 041. Raw snapshots and full-map
intermediates remain protected pending synthesis acceptance and an explicit
lifecycle/compaction decision.

## Boundaries

No PLUTO run, particle output, radio/PRAiSE product, >50 Myr extension,
scientific-default change, raw deletion, commit, push, Stas/Patrick escalation,
or `agent_comms` edit occurred. No common-age science result is claimed until
the three returned case products and the endpoint merge validate.
