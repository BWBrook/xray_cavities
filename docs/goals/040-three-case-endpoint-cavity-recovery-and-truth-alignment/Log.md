# Goal 040 Log - Three-case endpoint cavity recovery and truth alignment

## Objective

Recover X-ray-only cavity candidates for the accepted C-HI, C-LO, and G-LO
50 Myr endpoints at `0/45/90 deg`, validate them against projected tracer
truth, and extract common Level 1/2 plus pressure context for final alignment.

## Local method development

The protocol was designed in
`docs/superpowers/specs/2026-07-12-three-case-cavity-recovery-design.md`.

A physical-scale 2-D Gaussian background was implemented and tested first,
then rejected by a real-map diagnostic because it selected field boundaries
rather than cavities. The accepted protocol uses a tracer-blind azimuthal
median radial profile, a 180 kpc background field, a 120 kpc candidate
aperture, and a 25 kpc2 component gate.

The implementation followed red-green TDD:

```text
uv run pytest tests/test_three_case_cavity_recovery.py -q
initial: 8 failures because the module was absent
green: 9 passed

uv run pytest tests/test_build_three_case_cavity_recovery.py -q
initial: 2 failures because the builder was absent
green with recovery suite: 11 passed

uv run pytest tests/test_three_case_endpoint_truth_alignment_wrapper.py -q
initial: 4 failures because the wrapper was absent
green: 4 passed
```

Final integrated focused suite before staging:

```text
uv run pytest tests/test_build_three_case_cavity_recovery.py \
  tests/test_three_case_cavity_recovery.py \
  tests/test_three_case_endpoint_truth_alignment_wrapper.py -q
15 passed

bash -n scripts/kunanyi/three_case_endpoint_truth_alignment.pbs
passed

git diff --check
passed
```

The final retrieval audit exposed a projected-pixel-area bug in the base
candidate selector. A new unequal-pixel-area regression test failed first,
then passed after candidate fractions were changed from pixel-count weighting
to projected-physical-area weighting. The corrected selector is now used by
the base protocol and all 135 sensitivity rows.

## Local result

`scripts/science/build_three_case_cavity_recovery.py` generated the compact
Goal 040 local surface. The corrected base method returns two opposite-side
components for all nine panels and selects approximately `432-452 kpc2` of
projected physical area. At tracer threshold `5e-3`, X-ray-mask precision is
`1.0`, while tracer recall spans `0.0208-0.2015`. The observer-side mask is
therefore a high-purity subset of the tracer surface, not a substitute for
tracer lobe volume.

The 135-row method sensitivity table preserves radial-profile and threshold
dependence. Broader candidate fractions expose topology instability in some
oblique panels, so no final topology is frozen.

Corrected geometric-depth base volumes are `5.48e3-5.96e3 kpc3` for C-HI,
`5.16e3-5.18e3 kpc3` for C-LO, and `5.18e3-5.20e3 kpc3` for G-LO. The rejected
pixel-count result had produced false view dependence and was not retained.

## Direct worker evidence

A `luna_high_executor` direct-profile worker implemented the first local
recovery engine and tests within a strict two-file boundary. Persisted runtime
metadata records GPT-5.6 Luna, high reasoning, workspace-write, recursion
disabled, return code zero, and no timeout. Root review independently reran
the tests, audited projected-axis aliases, rejected the first real-map
Gaussian result, and implemented the accepted radial-profile refinement.

A prior `sol_high_specialist` protocol worker timed out without a final
report. Its one retained observation, independently verified by root, was
that a 41-pixel filter is not a common physical scale across views. No other
claim from that incomplete run was accepted.

After retrieval, one `luna_high_executor` minimal-context worker was dispatched
to implement the mechanically specified truth-alignment builder and tests. The
runner recorded GPT-5.6 Luna / high, workspace-write, recursive dispatch
disabled, but timed out at 300 seconds with no usage record. Per policy it was
not retried or escalated. Root inspected the partial files, repaired the
temporary-output and CSV-reader defects, reran the red/green tests, and
independently audited every base formula and manifest before acceptance.

## Remote preflight and submission

Chrome/Open OnDemand refreshed the five-minute TPAC selector. Terminal-first
repo helpers then staged under:

`/u/bwbrook/codex_kunanyi/goal040_three_case_endpoint_truth_alignment`

Staged SHA-256 values matched local:

```text
d01d9be561440937a60ca5872112fe6fe149d6e6c4b81acb29e9f0eef43923a3  pluto_h5_truth_extract.c
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  pluto_h5_cavity_stub_extract.c
34672781c3d8ccd935a8823f88654d013815925f04500e759535ceb0fb3d1dc7  three_case_endpoint_truth_alignment.pbs
```

Remote wrapper syntax passed. All three endpoint files were readable, exactly
`44,890,581,676` bytes, and contained `rho`, `prs`, `tr1`, `vx1`, `vx2`, and
`vx3` under their accepted timestep groups. The target analysis root was
absent before submission.

Exactly one job was submitted:

```text
756092.kunanyi-ohpc
Job_Name = tri_truth
job_state = Q
queue = normal
qtime = Sun Jul 12 22:46:27 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

## Status

`complete_product`

Decision label:
`THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE`.

Barry reported completion for `756092.kunanyi-ohpc`. Final qstat records
`job_state=F`, `Exit_status=0`, walltime `00:22:16`, and
`Stageout_status=1`. Stderr is empty; all three case validation markers and
`three_case_truth_validation=passed` are present. The compact 24-member archive
was retrieved, its internal checksums passed, and its SHA-256 is
`474c06f81d09acdb616345bc56d7919738d894d317b0d98a1fee7f941b9d2e6b`.

At base tracer threshold `5e-3`, Level 2 / Level 1 energy is `0.439876` for
C-HI, `0.638114` for C-LO, and `0.507338` for G-LO. The corrected geometric
X-ray volume / Level 2 volume spans `0.00740-0.00804`, `0.3906-0.3918`, and
`0.0655-0.0656`, respectively. Side-specific tracer-shell pressures were
combined with X-ray volumes only as explicitly labelled hybrid `pV`, `2.5pV`,
and `4pV` proxies.

Final acceptance validation:

```text
uv run pytest tests/test_three_case_cavity_recovery.py \
  tests/test_build_three_case_cavity_recovery.py \
  tests/test_build_three_case_truth_alignment.py \
  tests/test_three_case_endpoint_truth_alignment_wrapper.py -q
21 passed

bash -n scripts/kunanyi/three_case_endpoint_truth_alignment.pbs
passed

remote archive checksum validation
22 compact files passed

local asset manifest validation
43 files passed

structured CSV/formula/metadata validation
passed: 10 CSV surfaces, 9 base rows, 135 method rows, 2 metadata files

visual inspection
both PNG products are nonblank, coherent, and correctly labelled

git diff --check
passed
```

## Boundary

No PLUTO production or continuation, XRAiSE rerun, PRAiSE/radio work,
source-age sweep, scientific-default change, bulky HDF5/particle retrieval,
commit, push, accepted-asset overwrite, Stas/Patrick escalation, or
`agent_comms` edit occurred.
