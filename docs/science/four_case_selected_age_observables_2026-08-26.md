# Four-case selected-age observables

## Purpose

Goal 064 turns the completed matched four-case production set into the first
common-age observable surface. It processes `C-HI`, `C-LO`, `G-HI`, and
`G-LO` at `10/20/30/40/50 Myr`, retaining the actual HDF5 time rather than
assuming the nominal label is exact.

This is a substantive analysis tranche, not another readiness packet. It will
produce:

- X-ray and tracer projections at `0/45/90 deg`;
- X-ray-only cavity recovery with tracer used only as a post-hoc truth check;
- conditional `pV`, adopted `2.5pV`, and comparison `4pV` cavity energies;
- corrected PRAiSE2 lossless and full-loss luminosities at
  `0.15/0.5/1.4/4.5/15 GHz` and `0/45/90 deg`;
- compact inputs for later synthesis with the accepted Goal 062 fluid,
  gravitational, and shock surface.

## Scientific contract

The factorial treatments are cluster/group environment crossed with
low/high one-sided jet power. Known bipolar jet power is twice the configured
one-sided value. The two primary paper tests remain:

1. cavity-energy bias versus valid shock Mach number;
2. cavity- and radio-inferred jet power versus known bipolar input power.

The X-ray observer mask is the accepted X-ray-only one-percent projected-area
deficit method. Tracer cannot determine that mask. A cavity energy is
quantitative only when the observer recovery yields exactly two non-crossing
components on opposite sides of the midplane. Other topologies remain visible
as explicitly nonquantitative proxies rather than being discarded or forced
into a two-cavity interpretation.

Ambient pressure remains the tracer-shell midpoint proxy. That is sufficient
for this comparative prove-out, but it is not an X-ray-fitted pressure and
must remain labelled in every energy row.

Corrected PRAiSE2 uses source commit
`73210e15d4c60e77ffb317b3ee2b9209c049edd4`. Each case builds its own complete
`0..5000` particle-history cache from the canonical matched run. Particle
coordinates used in a radio view must be drawn from the exact causal source
output selected by PRAiSE2 and may never be later than the paired fluid age.

## Validity boundary

The `G-HI` 50 Myr endpoint remains valid for X-ray, cavity, radio, and other
non-shock observables. It is not valid for shock-kinematic regression. Use
`G-HI` shock positions only through snapshot `47` and centred speed/Mach
values only through snapshot `46`. The other three cases remain shock-valid
through snapshot `50`.

## Execution design

The calculation is split at real failure and restart boundaries:

- one four-core job computes the lighter X-ray/cavity surface, with one case
  per process;
- four independent 16-core radio jobs compute one complete particle history
  and selected-age radio surface per case.

This is not a ladder of exploratory runs. It is the full prespecified common-
age surface, separated so a failure in one long particle history does not
invalidate or restart the other cases. Raw HDF5 and particle products remain
remote and read-only. Transient history caches remain remote until compact
outputs are retrieved and validated.

## Submission

The remote preflight passed for all `20` selected HDF5 surfaces, all four
exact `0..5000` canonical particle sequences, the Goal 062 fluid manifests,
the reviewed PRAiSE2 source hash/import, the staged wrappers, and the enabled
`normal` queue. The no-overwrite analysis root was absent.

Five jobs were submitted and verified running once:

- `787293.kunanyi-ohpc` / `four_xcav`: four-case X-ray/cavity surface;
- `787294.kunanyi-ohpc` / `c_hi_selrad`: `C-HI` radio history and products;
- `787295.kunanyi-ohpc` / `c_lo_selrad`: `C-LO` radio history and products;
- `787296.kunanyi-ohpc` / `g_hi_selrad`: `G-HI` radio history and products;
- `787297.kunanyi-ohpc` / `g_lo_selrad`: `G-LO` radio history and products.

All five first-attempt jobs then exited at launch with `Exit_status=1`. The
four radio stderr logs directly record `OSError: [Errno 122] Disk quota
exceeded` while creating their initial analysis manifests on scratch. The
X-ray job failed in the same ten-second launch interval with empty case
outputs, so its shared cause is inferred rather than directly printed. No
HDF5/XRAiSE/PRAiSE2 science computation started and no reusable science output
was lost.

The failed-attempt logs, final scheduler records, and job identifiers are
preserved locally and in a stable file-list archive with SHA-256
`266c29b736e6e0d88b991f87daa4b29fbc7f584d918e543cba5462fbe99246ef`.
The failed scratch analysis root remains untouched.

The narrow repair moved only transient Goal 064 analysis and history-cache
output to the enlarged home allocation under
`/u/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables`.
Raw production inputs remain remote, read-only, and unchanged. Regression
tests now require both wrappers to use home rather than the full scratch
allocation.

Five replacement jobs were submitted and verified running once:

- `787301.kunanyi-ohpc` / `four_xcav_r1`;
- `787302.kunanyi-ohpc` / `c_hi_selr1`;
- `787303.kunanyi-ohpc` / `c_lo_selr1`;
- `787304.kunanyi-ohpc` / `g_hi_selr1`;
- `787305.kunanyi-ohpc` / `g_lo_selr1`.

The PBS stop rule was invoked after the replacement running-state proof.
Completion, retrieval, validation, and synthesis await Barry's PBS emails or
an explicit re-check request.

## Radio dependency repair

At Barry's next authorized re-check, `C-HI`, `G-HI`, and `G-LO` had returned
`Exit_status=1`; the X-ray and `C-LO` jobs were still running at that snapshot.
The later `C-LO` completion email also reported `Exit_status=1`. All four
failed radio stderr logs report the same import error:
`ModuleNotFoundError: No module named 'plutokore.radio.praise'`.

This occurred after each job had successfully built its complete `5001`-output
history cache. Recorded endpoint counts are `196732`, `193741`, and `197568`
for `C-HI`, `G-HI`, and `G-LO`; the C-LO resume preflight separately confirmed
its complete cache attributes, but did not persist its byte size or endpoint
count in the compact log. All four caches are reusable. The missing files were
runtime support modules, not a scientific-method or data failure.

The radio wrapper now requires and imports both `praise.py` and
`raytracing.py` before beginning cache work. A separate immutable repair stage
contains those files from the same reviewed plutokore commit, plus the
corrected `praise2.py`. Remote hashes, wrapper syntax, dependency APIs, cache
completion attributes, and no-overwrite analysis roots all passed.

Four cache-resume jobs were submitted and verified running once:

- `787310.kunanyi-ohpc` / `c_hi_selr2`;
- `787329.kunanyi-ohpc` / `c_lo_selr2`;
- `787311.kunanyi-ohpc` / `g_hi_selr2`;
- `787312.kunanyi-ohpc` / `g_lo_selr2`.

The active `C-LO` job's original stage was not changed beneath it. After its
matching completion evidence arrived, its cache was resumed from the separate
repair stage. The PBS stop rule applies to all four resume jobs; the X-ray job
remained running at the last authorized scheduler snapshot.

Status: `submitted_waiting_pbs_completion`.

## X-ray concurrency repair

The four-case X-ray replacement, `787301.kunanyi-ohpc`, reached the science
calculation but exhausted its shared memory envelope. It used
`126641000kb` of the requested `128gb`. C-HI, C-LO, and G-LO nevertheless
completed successfully; only G-HI failed (`137`, signal 9) after its manifest
preflight. These three products are retained for final packaging.

The execution wrapper now permits one explicitly selected case while retaining
the four-case default. A separate G-HI-only job, `787415.kunanyi-ohpc`, was
verified running with the full `128gb` node available to that case. This
repair changes execution concurrency only: inputs, ages, views, cavity method,
and scientific gates are unchanged. The PBS stop rule remains active.

## Partial radio completion

C-HI and G-HI are the first complete Goal 064 radio products. Jobs `787310`
and `787311` both exited `0`, produced empty stderr, and passed their remote
`radio_validation` contracts. Local review confirmed the prespecified five
ages, five frequencies, two loss models, three viewing angles, corrected
PRAiSE2 provenance, finite positive luminosities, and causal particle-source
selection.

These products are accepted as partial-green inputs but are not yet a
factorial result. C-LO and G-LO were still running at the authorized snapshot;
cross-case synthesis waits for those completion records. The compact C-HI and
G-HI products and immutable retrieval evidence are under
`completed_radio_pair_1/`.

## G-LO radio and four-case X-ray completion

G-LO radio job `787312.kunanyi-ohpc` and the isolated G-HI X-ray repair
`787415.kunanyi-ohpc` both finished with `Exit_status=0` and empty stderr.
The retrieved G-LO radio product passed the complete local contract: `50`
primary rows, `150` viewing rows, `15` source rows, `6` particle-summary
rows, finite positive luminosities and magnetic fields, exact selected
ages/frequencies/loss models/views, causal particle-source matching, and the
reviewed corrected-PRAiSE2 commit.

The G-HI repair passed all `15` selected age/view projection checks with no
empty projected columns and finite positive corrected X-ray summaries. The
successful C-HI, C-LO, and G-LO compact products from the original X-ray job
were combined with the repaired G-HI output using a stable file-list archive;
no HDF5 or XRAiSE calculation was rerun. The complete four-case archive has
SHA-256
`359b9e2fd4d6b87309177adefcab86b34c22a9645fb1c1da8f1deb192a343d3e`,
`68` members, and `60` case-age-view projection rows.

The cavity validity gate remains fail-closed. In particular, early 90-degree
C-LO and G-LO rows with no significant recovered component retain zero energy
and `quantitative_energy_valid=False`; they are not promoted into synthetic
cavity measurements.

Goal 064 is not yet a factorial result. C-HI, G-HI, and G-LO radio plus the
complete four-case X-ray/cavity surface are green; C-LO radio `787329` was
still running at the one authorized scheduler snapshot. No cross-case
synthesis has begun.

Status: `submitted_waiting_pbs_completion`.

## Final C-LO radio completion

C-LO radio job `787329.kunanyi-ohpc` finished with `Exit_status=0` in
`05:40:55`; stderr is empty. Its compact archive has SHA-256
`118227510131c1b728fcbf3e9d11b53a9c378a4634c48a52feb582456c345678`.
Local review passed the same prespecified contract as the other cases:
`50` primary rows, `150` viewing rows, `15` source rows, `6` particle-summary
rows, finite positive luminosities and magnetic fields, exact selected
ages/frequencies/loss models/views, causal particle-source matching within
numerical tolerance, and corrected-PRAiSE2 commit
`73210e15d4c60e77ffb317b3ee2b9209c049edd4`.

The complete Goal 064 radio surface therefore contains `200` primary rows,
`600` viewing rows, and `60` source rows across C-HI, C-LO, G-HI, and G-LO.
Together with the validated `60` case-age-view X-ray/cavity surface, this
completes the prespecified selected-age observable tranche. No cross-case
interpretation is claimed here; the package is now the verified input for the
next synthesis with Goal 062/063 fluid, gravity, background, and shock data.

Decision: `FOUR_CASE_SELECTED_AGE_OBSERVABLE_SURFACE_COMPLETE_SYNTHESIS_READY`.

Status: `complete_product`.
