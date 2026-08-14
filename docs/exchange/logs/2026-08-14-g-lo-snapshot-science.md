# 2026-08-14 - G-LO snapshot science

Goal 058 begins the analysis phase on the complete retained G-LO evidence
surface while the other three matched factorial cases await storage approval
and production.

The local implementation now provides reusable single-case modules for:

- canonical retained-snapshot discovery and provenance;
- fractional-primary plus binary-sensitivity tracer partitions;
- ambient/lobe thermal, kinetic, gravitational, and closure accounting; and
- two-sided shock positions, speeds, and Mach-number diagnostics.

The live remote inventory found six retained float snapshots at
`0/10/20/30/40/50 Myr`, exactly matching the accepted Goal 057 manifest. The
draft wrapper was corrected before submission from an unsupported 51-snapshot
assumption to this complete retained chain. No ages were substituted or
interpolated.

PBS `785483.kunanyi-ohpc` / `g_lo_fluid` was submitted and verified running in
`normal` with one CPU, `64gb`, and `48:00:00` walltime. The job reads the six
remote HDF5 files in place and is expected to produce compact CSV/JSON evidence
plus a stage-root archive at:

`/u/bwbrook/codex_kunanyi/goal058_g_lo_snapshot_science/g_lo_fluid_snapshot_science_2026-08-14.tar.gz`

The PBS stop rule is active. Resume only after Barry reports the completion
email or explicitly authorises a scheduler re-check. A green fluid result will
then feed the existing X-ray/cavity surface, corrected-PRAiSE2 radio products,
and inferred-power synthesis; no cross-case claim is authorised in Goal 058.

Barry subsequently reported the job complete with `Exit_status=1`, zero CPU
time, and `00:00:13` walltime. Read-only retrieval found that every input and
science preflight passed; the wrapper failed before analysis because Kunanyi's
Bash treated expansion of an empty optional-argument array as an unbound
variable under `set -u`. The repair uses portable positional arguments and
retains the failed scheduler record as provenance. No HDF5 analysis occurred
in the failed attempt.

The repaired wrapper and input-hash manifest passed local and remote checks.
PBS `785485.kunanyi-ohpc` / `g_lo_fluid` was submitted and verified queued in
`normal`; the stop rule was reinstated immediately. The first failed attempt
is not being rewritten or treated as science output.

Barry then reported the repaired fluid job complete with `Exit_status=0` and
`00:26:13` walltime. The final job record, six completion markers, compact
archive, and zero-byte stderr all passed. The retrieved archive SHA-256 is
`44312bac8f208fcf599e6d86995ccce1768acb094ec04a50fd23eef3260449ed`.
The result preserves rather than conceals the energy-accounting limitation:
because boundary flux is unmeasured from the retained snapshots, the closure
residual becomes increasingly negative and remains explicitly unattributed.

The corrected-PRAiSE2 radio packet was then staged with the full small
`plutokore` source package required by its low-level emissivity and ray-tracing
helpers. All `38` staged hashes, the exact corrected commit, the complete
`197568 x 5001` retained history cache, the causal particle roots, and the
five-age/five-frequency/three-view contract passed. PBS
`785488.kunanyi-ohpc` / `g_lo_radio` was submitted and verified running in
`normal` with 16 CPUs, `96gb`, and walltime `48:00:00`.

The PBS stop rule is active again. Resume only after Barry reports completion
or explicitly authorises a re-check. A green radio result will be retrieved
compactly and joined locally to the accepted X-ray/cavity evidence, the fluid
surface, the spectral-age fits, and the inferred-power synthesis. No
cross-case claim is authorised in Goal 058.

While the radio job runs, the final assembler was rehearsed locally against
the retrieved real fluid tables and accepted X-ray/cavity surface. Disposable
synthetic radio rows were used only to exercise the pending schema and were not
retained as evidence. The audit replaced the weak radio-view row-count gate
with an exact age/view/loss/frequency uniqueness check and requires the primary
radio table to equal its `45deg` rows. The real-input rehearsal and `33`
focused tests pass. No scheduler query was made.

The final builder is now case-generic rather than G-LO-specific. Its locked
contract covers `C-HI`, `C-LO`, `G-LO`, and `G-HI`, including the correct
cluster/group atmosphere identity and `1e43/1e45 erg s^-1` one-sided power.
Known-power inference uses the corresponding bipolar value, and source truth
must agree with the energy table. A high-power contract test plus the real
G-LO rehearsal bring the focused total to `34` passing tests. This is pipeline
preparation only; it does not create a cross-case result.

A setup-first provisional science note now records the real fluid and accepted
X-ray/cavity results. It treats the increasingly negative zero-boundary closure
as unresolved rather than cocoon energy, reports the `2.15-2.86` kinematic
Mach surface alongside the weak or unavailable jump-condition corroboration,
and preserves the 10 and 30 Myr X-ray topology exclusions. Radio-dependent
sections remain explicitly pending.

Barry reported PBS `785488.kunanyi-ohpc` / `g_lo_radio` complete with
`Exit_status=0` and `04:58:58` walltime. Final scheduler inspection confirmed
state `F`, the known `Stageout_status=1` caveat, `radio_validation=passed`, and
zero-byte stderr. The compact archive was retrieved directly from the stage
root; local and remote SHA-256 agree at
`c648d22e2059b3ec3464537b6a1992896bf1f20b0b0e37e952d7614d9dc1ce8b`.

The archive contains the exact five-age, five-frequency, two-loss-model, and
three-view contract: `50` primary `45deg` rows and `150` view rows. Corrected
PRAiSE2 commit `73210e15d4c60e77ffb317b3ee2b9209c049edd4` and source SHA-256
`eeee367581829b4dd779992c6b582a1676b796fc792b0bb70b8e9c13ee193895`
match the staged scientific method. Causal particle matching and finite
positive radio fields passed.

The real local synthesis completed without cross-case input. Its direct CLI
entry point was repaired after a focused smoke test exposed a repository-path
import failure that unit imports had hidden. The resulting product contains
`13` scientific tables, `7` generated diagnostic figures, the accepted X-ray
context pointer, input hashes, and explicit validation.

G-LO exposes opposite observer-method biases. Full-loss empirical radio-power
relations return central values about `3.1-7.1` times the known bipolar power,
while valid `45deg` cavity-plus-spectral estimates return about `0.074-0.541`
of known power depending on age, `2.5pV/4pV`, and magnetic-field treatment.
Every continuous-injection break remains above the observed `15 GHz` band, so
the spectral ages are upper limits and the associated cavity powers are lower
bounds conditional on method. The result supports method recovery analysis,
not a four-case scientific claim.

Decision:
`G_LO_SINGLE_CASE_PIPELINE_GREEN_RECOVERY_BIASES_EXPOSED_NO_CROSS_CASE_CLAIM`.
Goal 058 is complete.
