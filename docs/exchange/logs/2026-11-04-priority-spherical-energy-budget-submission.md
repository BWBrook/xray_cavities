# Priority: submit spherical energy budgets and resolve G-HI provenance

Date: 2026-11-04.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`).
Status: explicit priority and execution request; no PBS submission claimed.
Source repository revision: `6c33d1b6a1b5d7b3d9905dfdf641b9ae74e64058`.

## Supervisor instructions

> Tell Barry's agent to prioritise the input checks and submit the 100/300 km/s energy budgets. Don't hold up the other three simulations because of G-HI. Commit and push.

The supervisor subsequently asked about the G-HI directory issue and
explicitly requested that Barry resolve it as well.

## Priority submission sequence

1. Complete native case/configuration/environment and exact input-file
   verification for **C-HI, C-LO and G-LO independently**. Use accepted run,
   build, restart and migration evidence plus the extractor's input receipts.
   Do not bypass provenance checks or substitute synthetic receipts.
2. Stage the reviewed spherical extractor and its tests, then run the small
   native smoke documented in
   [the extractor guide](../../science/spherical_budget_extractor_2026-11-04.md).
   C-HI snapshot 1 against its actual snapshot 0 is the existing recommendation;
   a problem specific to that case should not prevent qualification of another
   ready case. Review the native smoke output before batch expansion.
3. Submit **both 100 and 300 km/s measurements for every available scientifically
   valid snapshot** of each ready case. Keep case-specific preflights and job
   dependencies so a G-HI failure cannot prevent the other three starting or
   erase their results. Use bounded native I/O and fresh output receipts; do
   not overwrite completed products or submit duplicate analyses.
4. Resolve G-HI's continuation provenance separately, then submit its valid
   snapshot chain. Preserve the existing exclusion of G-HI snapshots 48--50.
5. Record actual PBS job IDs/states, the cases/snapshots covered and any
   remaining case-specific blocker in the handover. Return the first measured
   result promptly rather than waiting for all four cases to finish.

The X-ray shock-finder validation is **not** a prerequisite for these budgets.
An uncertified 40-kpc cut is also not a reason to withhold an otherwise valid
uncut spherical measurement. Preserve source checks, unavailable radii,
domain-truncation, tracer-quality and boundary-overlap flags; retain explicit
scientific holds where appropriate rather than calling every result qualified.
Do not silently clip the primary budget or adopt a new boundary-safe width.

## Requested scientific output

For each actual snapshot time and each speed threshold, return:

- The raw radius from the full three-component speed, including the
  radius-defining cell and coverage/outlier checks.
- Thermal, kinetic and fixed-initial-potential gravitational energy changes,
  calculated cell by cell against the same initial cells, including **all**
  slower gas inside the sphere.
- Their sum divided by the actual case's bipolar injected energy, with the
  full-cell `tr1 > 1e-3` cocoon/ambient split.
- A table and time-series plots comparing 100 versus 300 km/s for each case,
  with a ratio-of-one reference and any missing/flagged records made explicit.

This is the requested first check of retained energy versus jet input.
Separately explain energy crossing the aperture and its time-varying radius
before interpreting a difference as numerical non-conservation. No new shock
selection is to be imposed on the gas entering these sums.

## G-HI issue: evidence and proposed resolution

The recorded failure is in `scripts/kunanyi/q031_flux_measurements.pbs`:

- Lines 107--110 compare dictionaries of all C/header hashes under the early
  and late `src` directories. The continuation has no duplicate `src` tree,
  so the early/late equality check fails before any case is measured.
- The same wrapper's `measure()` helper, lines 46--52, also hardcodes
  `--problem-source-dir` to the measurement root's `src`. The G-HI call uses
  the continuation root. Merely deleting or relaxing the equality assertion
  would leave this second missing-source failure.
- The original continuation staging manifest lists the executable,
  `pluto.ini`, environment/configuration and restart files but no `src` copy.
  This is consistent with a reused-binary continuation layout, not evidence
  that native output files disappeared during the latest analysis.
- The 4-November live check reported byte-identical early/late executables
  and `pluto.ini`. The retained restart-pair report has status `ok` and binds
  the 10-Myr fluid/particle checkpoint with hashes. These are useful existing
  evidence, not a replacement for qualifying the complete accepted lineage.

**Requested repair for review:** represent the continuation's verified source
build as inherited from its accepted parent, separately from the output and
configuration locations. Revalidate the parent source/build record, binary
hash, runtime/compiled configuration, atmosphere, grid, restart checkpoint and
canonical output chain. Explicitly pass the verified source directory to the
flux analysis and create independently valid input receipts for the spherical
extractor. Do not assume source-tree duplication is necessary to establish
identity, but do not accept matching labels or a missing parent as proof.

Add focused tests for the accepted inherited-source continuation and rejection
of mismatched executables/configurations/environments, missing parent source
evidence, and broken/ambiguous restart or snapshot chains. Preserve failed
stages and receipts, and use a new reviewed analysis stage for any resubmission.
Do not copy arbitrary or current source files into the old continuation to
make the existing assertion pass, rebuild the historical executable, or rerun
the simulation merely to repair analysis bookkeeping.

The original failed flux job and terminal dependent pilot are distinct from
the spherical submission request. Review their dependency chain separately;
do not attach the other three spherical cases to the failed G-HI-dependent
all-case wrapper.

## References and delivery status

- [Spherical extractor and native-smoke contract](../../science/spherical_budget_extractor_2026-11-04.md).
- [Recorded flux failure](2026-11-04-boundary-and-extractor-tranche.md).
- [Original continuation staging manifest](../../science/assets/g_hi_full_history_production_2026-08-20/home_continuation_786326/remote_logs/home_continuation_staging_manifest.txt).
- [Validated restart pair](../../science/assets/g_hi_full_history_production_2026-08-20/home_continuation_786326/completion/remote_logs/restart_pair_validation_job.json).
- `scripts/kunanyi/q031_flux_measurements.pbs` and
  `scripts/kunanyi/g_hi_full_history_home_continuation.pbs`.

This update is a repository handover requested by the supervisor. It does not
claim that the source-resolution repair has been implemented, that PBS jobs
have been submitted, or that Barry's agent has acknowledged it. No simulation
data, analysis code, acceptance threshold or historical receipt was changed.
