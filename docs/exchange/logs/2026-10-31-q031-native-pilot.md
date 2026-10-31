# Q-031 C-HI/G-HI native pilot

Barry authorised the fixed C-HI and G-HI 40 Myr pilot, including clamp
sensitivity, on 31 October 2026. This is post-processing of retained simulation
outputs. The accepted method is in
`docs/science/q031_native_path_length_design_2026-10-31.md`.

## Implementation and review

`build_q031_native_emission.py` reuses the exact Q-029 factor-1 shock-mask
helpers and strict float64 `tr1 > 1e-3` cocoon mask. Both cases require
quantitative bilateral shocks. It computes current and case-specific initial
emission through the current masks, at 0/45/90 degrees, using both retained
linear extrapolation and independently clamped table coordinates. Signed
contributions, table-domain coverage and pre-sanitization failures remain
visible. These are diagnostic products; numerical validation does not establish
the physical adequacy of either extrapolation convention.

Independent science review led to explicit regional volume/mass/emission
closures, Q-029 mass anchors, saved density/temperature distributions, separate
raw-kernel and corrected-emissivity failure diagnostics, and geometry refinement
checks. Independent launch review led to source binding against the validated
flux inputs, imported-library identity checks, mandatory real-kernel smoke
evidence, and transactional package verification.

Final science review also made the reference age/source/calibration fields
mandatory. It independently checked the asymmetric 90-degree projection against
the sign-reversed direct x-sum and chunked projections against one-pass
projections (maximum discrepancy `4.44e-16`). The final local six-file
deployment suite passed all 79 tests, including the real-kernel subprocess CLI.
Both frozen C-HI/G-HI reference bundles pass the strengthened binding checks.

The launch wrapper checks the completed ten-unit migration and its links,
rejects unresolved migration tombstones, and verifies the flux package before
any native reads. The selected native paths and metadata must match the flux
provenance. Device identifiers are recorded but not compared across allocations
because NFS device numbers can differ between nodes; the native process checks
them before and after its own read. Literal source paths and resolved paths are
both preserved.

The result package contains the six science outputs and manifest for each
case, dependency records before and after extraction, source/runtime checksums,
smoke evidence and per-case resource records. Native payloads and temporary
mask caches remain on Kunanyi.

## Resource and dependency plan

The target smoke uses 2 CPUs, 8 GB and a one-hour limit. The pilot uses 2 CPUs,
128 GB and a 24-hour limit, processing cases sequentially. Historical Q-029
mask extraction peaked near 41 GB; native inputs already reside on Kunanyi.
The pilot is submitted only after the target smoke passes, with explicit PBS
`afterok` dependencies on that smoke, migration `870323.kunanyi-ohpc` and flux
`870374.kunanyi-ohpc`. Receipt checks remain mandatory even after PBS releases
the dependency hold.

At 11:32 UTC, migration was running (7:42:51 elapsed) and flux was held behind
recovery/migration. Native scientific results are pending.

## Target smoke and runtime repair

Revision `df42e23` was staged as `q031_native_emission_2026-10-31_r1`.
The uploaded archive SHA-256 was
`e896073c60d8e4c93ec130a1e979829d1b62cb0c4317d0d869c65ffa05d91c8f`;
all source/reference/runtime checksums matched on Kunanyi.
Smoke job `870703.kunanyi-ohpc` stopped with exit 1 before pytest or native reads:
compute node `n002` lacks `/usr/bin/time`. The failed stage and logs remain intact.

The r2 wrapper instead uses `run_q031_measured.py`, based on Python's
`resource.getrusage(RUSAGE_CHILDREN)` and subprocess exit status. It preserves
measured peak RSS, elapsed/CPU time and nonzero failures without requiring an
external timing executable. Successful/failing-child and no-overwrite checks
pass; the packaging suite passes 20 tests. A fresh target smoke is required.

Smoke `870704` in r2 ran 81 tests: 78 passed and three failed because the
stage omitted `xray_cavity_method_ladder.py` and its local import dependencies.
The failure occurred while binding source hashes, before any native reads.
The revised staging builder recursively collects local science imports,
including imports inside functions. The r3 package adds that closure and is
tested in isolation before upload. No scientific algorithm or tolerance changed.

## r3 launch handoff

The isolated r3 stage passed all 81 tests locally in 8.37 seconds, including
the actual emission-kernel CLI. One local Astropy warning reported an ignored
nonexistent `XDG_CONFIG_HOME`; no test failed. The stage contains 40 files and
is bound to source commit `61fb74515d6f1674b1fe42c384bf2972c271f47d`.
Its archive SHA-256 is
`d190b526f16f5471b3c8843e0cb766aef00a571abeec62a2dc97b8d3547def75`.
The remote archive hash and all static/runtime checksums matched.

Target smoke `870705.kunanyi-ohpc` was submitted. At 11:47 UTC the Mac was
locked, preventing inspection through the authenticated portal. Barry has been
asked to unlock it; Claude has the same handoff on discussion 29. The native
job has not been submitted and target-smoke completion is not claimed.

Resume through the existing portal shell. Check `qstat -xf 870705`,
`run_smoke/run.out`, `run_smoke/resources.txt` and `run_smoke/completion.json`
in the r3 stage. Only after successful target smoke, submit the native mode
with explicit `afterok` dependencies on `870705`, `870323` and `870374`,
then verify the resulting job's hold/dependency state. Keep the existing
wrapper receipt gates. No scheduled monitoring was created.

Post-run scientific review must inspect table-domain occupancy, nonfinite
sanitization, finite-negative linear emission and linear-versus-clamp
sensitivity before using brightness or shell-budget conclusions.

## Resumed after unlock

Barry unlocked the Mac. Target smoke `870705` finished `F/1`, with 79 tests
passed and two failed. Both failures were at `shutil.rmtree(args.cache_dir)`
after science outputs and their manifest had been written: `OSError 39`,
`ratios_and_masks` directory not empty. Cache mappings were still open, which
prevents normal unlink-and-remove cleanup on NFS. The stage remains preserved.
Measured child peak RSS was 232,584 KiB and elapsed time 127.804587 seconds;
PBS reported 2:08 walltime. Native submission remains held pending the narrowly
repaired target smoke. No native HDF5 data have been read by these smoke jobs.

## Successful target smoke and dependent native submission

The narrow mapping-lifetime repair is source commit `fe0c0cb`. Independent
review confirmed all seven cache mappings close after their final use and
before cleanup. The regression asserts closure at the deletion boundary;
`--keep-cache` retains flushed files while closing handles. The isolated r4
stage passed 82 tests locally, including the actual kernel CLI.

The r4 archive contains 40 files (231,720 bytes), SHA-256
`d6dbc8cfae9b41acaf7175ae3885006e195f783f7ac5dee22ecb1ac5575dedff`.
All archive, source, reference and runtime hashes matched on Kunanyi.
Target smoke `870712.kunanyi-ohpc` finished `F/0` with **82 passed, zero
skipped**, pytest time 110.63 seconds, measured wall time 112.577670 seconds,
peak RSS 231,160 KiB and PBS walltime 1:55. The receipt was independently
rechecked against staged files and imported runtime identities before launch.

Native pilot **`870719.kunanyi-ohpc`** was submitted at 23:00 AEDT and verified
as `H`, system hold, with exact `afterok` dependencies on `870712`, `870323`
and `870374`. Resources are 2 CPUs, 128 GB and 24 hours. At 12:00:35 UTC the
migration remained running and flux remained held. This records successful
launch preparation and a dependency-held submission, not native results.

The downloaded six-file smoke/launch evidence archive has SHA-256
`8fecfa13460a7e5c53b390066b2338137db0a63bb0afd4318a49f1856dca0b18`.
Its member set, archive hash, JUnit count/no failures/no skips, receipt hashes,
stage/runtime manifests and native dependency/resource fields were checked
locally. Extracted evidence is under
`docs/science/assets/q031_native_pilot_2026-10-31/stage_r4/remote_evidence/`.
The staging builder, local JUnit and launch record are retained alongside it.

Next check: inspect existing job `870719` and its prerequisites, then review
its packaged results if successful. Do not submit a duplicate or weaken the
receipt gates. Claude receives this launch evidence on discussion 29. No
scheduled monitoring or new simulation was created.
