# Three-case common-age evolution

Date: 2026-07-13

Status: `complete_local_synthesis`

Decision label:
`THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE`

## Purpose

Goal 041 extends the accepted 50 Myr three-case control surface into a common
age axis using existing production outputs. It will compare C-HI, C-LO, and
G-LO at nominal ages `10/20/30/40/50 Myr` and views `0/45/90 deg` without a
new PLUTO run.

This is a full existing-output evolution analysis, not a pilot. It is also not
a publication-ready observable or a final topology claim.

## Age selection

Each source was selected from the HDF5 `Time` attribute, not from its filename
or output index. The selection tolerance is `0.05 Myr`; every selected surface
is within `0.001 Myr` of its nominal age.

| Case | 10 Myr | 20 Myr | 30 Myr | 40 Myr | 50 Myr |
| --- | ---: | ---: | ---: | ---: | ---: |
| C-HI output index | 10 | 20 | 30 | 40 | 51 |
| C-LO output index | 11 | 23 | 33 | 43 | 53 |
| G-LO output index | 10 | 20 | 30 | 40 | 50 |

All selected and baseline files expose `rho`, `prs`, `tr1`, `vx1`, `vx2`, and
`vx3` on the same `1014 x 960 x 960` grid. The Level 3 baseline for every case
is its exact `Timestep_0` surface with `Time=0`.

## Analysis contract

At `10/20/30/40 Myr`, each case job will generate:

- XRAiSE raw, corrected, correction-ratio, and projected-tracer maps at
  `0/45/90 deg`;
- Level 1 injected-energy and Level 2 tracer-lobe truth;
- tracer-defined side geometry and ambient-shell pressure context;
- the accepted Goal 040 physical-area X-ray recovery surface;
- the complete 15-protocol recovery sensitivity grid for each view;
- cavity energy and power tables under minor, geometric, and major depth
  assumptions and `pV`, adopted `2.5pV`, and `4pV` conventions.

At `50 Myr`, X-ray recovery, Level 1/2 truth, and cavity context are reused from
the hash-locked accepted Goal 040 endpoint. They are not recomputed. Level 3
thermal plus kinetic ambient-energy change is computed at all five ages
against the exact same-case zero-time baseline. Gravitational Level 3 remains
excluded because no reviewed potential and zero-point convention exists.

The zero-degree projection uses `direct_y_axis_sum`; nonzero views use
`edge_overlap_uniform_cell_projection`. Tracer masks remain post-hoc
validation targets and do not define the X-ray recovery mask.

## Method boundaries

Side-specific ages and powers are reported only when the observer-side result
contains exactly one non-crossing component on each side. Otherwise the
result is restricted to a bipolar volume with mean shell pressure and no
side-age estimate.

The analysis is descriptive. It does not add radio observables, p-values,
causal identification, a final cavity topology, or publication-facing claims.

## Storage and lifecycle gate

The capacity forecast uses the measured accepted three-view XRAiSE TSV surface
of `198,678,477` bytes, scaled to four new ages per case, plus a one-age
transient allowance and a conservative compact archive/log allowance. Across
the three jobs the forecast is `3,434,141,724` bytes; with 20 percent safety it
is `4,120,970,069` bytes. Live scratch availability was
`3,204,297,185,558,528` bytes and the write probe passed.

Full map arrays remain remote under the three analysis roots. Compact
CSV/JSON/log/checksum/provenance archives are the retrieval products. Selected
raw HDF5 surfaces and zero-time baselines remain protected until Goal 041
synthesis is accepted; deletion requires Barry's explicit approval.

## Submission And Runtime Repair

The original three one-node jobs entered PBS correctly, started immediately,
and then failed within `8-12` seconds with `Exit_status=1`. All three passed
their manifest and scratch gates; the first compiled truth-extractor launch
failed because `libsz.so.2` was no longer on the runtime library path after the
wrapper purged the HDF5 module environment. This was a shared wrapper-runtime
defect, not a data, method, storage, or queue failure.

The wrapper now retains the HDF5 dependency paths while adding Anaconda and
fails closed if `ldd` reports an unresolved dependency for either compiled
extractor. The combined Python/HDF5 stack and all six existing case extractor
binaries passed a remote runtime preflight. The failed roots were preserved.

Three repaired retries were submitted to new no-overwrite roots on `normal`:

| Case | Job | State at stop | Resources |
| --- | --- | --- | --- |
| C-HI | `770758.kunanyi-ohpc` / `c_hi_ageev_r1` | `Q` | 1 CPU, 96 GB, 12 h |
| C-LO | `770759.kunanyi-ohpc` / `c_lo_ageev_r1` | `Q` | 1 CPU, 96 GB, 12 h |
| G-LO | `770760.kunanyi-ohpc` / `g_lo_ageev_r1` | `Q` | 1 CPU, 96 GB, 12 h |

The PBS stop rule was re-invoked immediately after all three retry jobs had one
verified `Q` record. The next scheduler check occurred only after Barry
explicitly requested a sanity check when no completion emails arrived.

## Retry Completion And Retrieval

All three retries started immediately at `2026-07-14 21:52:11 +10:00` and
finished green around midnight:

| Case | Job | Exit | Walltime | End time |
| --- | --- | ---: | ---: | --- |
| C-HI | `770758.kunanyi-ohpc` / `c_hi_ageev_r1` | 0 | `02:16:43` | `2026-07-15 00:08:54 +10:00` |
| C-LO | `770759.kunanyi-ohpc` / `c_lo_ageev_r1` | 0 | `02:22:12` | `2026-07-15 00:14:23 +10:00` |
| G-LO | `770760.kunanyi-ohpc` / `g_lo_ageev_r1` | 0 | `02:22:59` | `2026-07-15 00:15:10 +10:00` |

Every final scheduler record reports `Stageout_status=1`. This is retained as
a scheduler caveat and may be related to the missing completion notifications,
but the exact notification failure mechanism is not established. The required
stage-root stdout, stderr, and compact archives were present: all three stderr
files are empty, all archives open with `tar -tzf`, and every extracted compact
product passes its internal SHA-256 manifest.

Each case metadata file reports
`complete_case_product_pending_endpoint_merge`. The three compact products now
contain Level 1/2 truth, Level 3 thermal-plus-kinetic ambient energy,
projection validation, X-ray recovery and sensitivity, and cavity
energy/power tables for the planned common-age surface. This establishes
case-product completion, not final Goal 041 synthesis: the next step is the
local merge with the accepted Goal 040 endpoint and cross-case interpretation.

## Local Synthesis And Power Binding Correction

The local endpoint merge found a material Goal 041 packaging error before any
cross-case interpretation was accepted. The returned C-HI source manifests
used one-sided jet power `1e44 erg/s`; the frozen three-case specification,
Meeting 2 action plan, C-HI production wrappers, and accepted Goal 040 endpoint
all use `1e45 erg/s`. C-LO and G-LO were already correct at `1e43 erg/s`.

The retrieved archives and case products remain unchanged as provenance. The
synthesis records the discrepancy in `correction_register.csv`, recomputes
C-HI Level 1 injected energy at 10-40 Myr from the authoritative power and
actual HDF5 time, and recalculates only ratios that depend on Level 1. Level 2,
Level 3, X-ray, geometry, pressure, and shell-age values are not rescaled or
recomputed. The accepted Goal 040 C-HI endpoint is retained unchanged. The
case builder and PBS preflight now fail closed on future case-power drift.

The definition-preserving merge produces 15 case-age truth rows, 45
case-age-view observer rows, 963 long-form hybrid-energy rows, and 45 method
sensitivity summaries. Headline observed trajectories are:

- C-HI Level 2 total / elapsed injection decreases from `0.513` at 10 Myr to
  `0.440` at 50 Myr, while Level 3 thermal-plus-kinetic / injection rises from
  `0.722` to `0.888`.
- C-LO Level 2 / injection rises from `0.480` to `0.638`; Level 3 / injection
  rises from `3.32` to `12.46` and is strongly thermal dominated.
- G-LO Level 2 / injection is comparatively stable (`0.461` to `0.507`), while
  Level 3 / injection rises from `0.871` to `1.091`.
- At 10 Myr, the fixed base observer method has a quantitatively valid
  two-component topology in only one of three C-HI views and in no C-LO or
  G-LO view. All nine 50 Myr case/view panels are valid under the base rule,
  but method sensitivity remains material, especially for C-LO.

These are normalized descriptive responses, not a closed energy partition.
Level 2 follows energy inside a changing tracer-selected volume; Level 3 is a
baseline-subtracted thermal-plus-kinetic change in a changing ambient mask and
excludes gravity. Ratios above one are therefore not automatically errors or
efficiencies. Ages and views are repeated states and deterministic projection
perturbations of one simulation per case, not independent replicates.

The C-HI/C-LO and C-LO/G-LO contrasts are descriptive associations with jet
power and environment under the fixed three-case design. They are not causal
effects because each contrast is represented by a single simulation per case.

## Products

Local submission evidence is under:

`docs/science/assets/three_case_common_age_evolution_2026-07-13/`

The remote stage root is:

`/u/bwbrook/codex_kunanyi/goal041_three_case_common_age_evolution`

Original failed roots are retained under:

`/scratch/bwbrook/xray_cavities_analysis/2026-07-13-three-case-common-age-evolution`

Retry analysis roots are children of:

`/scratch/bwbrook/xray_cavities_analysis/2026-07-14-three-case-common-age-evolution-retry1`

The compact retry archives and combined output logs are retrieved and
validated independently. The local synthesis is under:

`docs/science/assets/three_case_common_age_evolution_2026-07-13/synthesis/`

It contains machine-readable provenance, truth, observer, hybrid, sensitivity,
contrast, correction, and validation tables plus two reviewer-facing figures.
No further remote compute is required for Goal 041. Raw snapshots and remote
full-map intermediates remain protected until this synthesis is accepted and a
separate Barry-authorized lifecycle/compaction decision is recorded.
