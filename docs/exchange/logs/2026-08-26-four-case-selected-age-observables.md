# 2026-08-26 - four-case selected-age observables

Goal 064 implements the first common-age observable surface for the completed
matched factorial. It uses all four cases at `10/20/30/40/50 Myr`, with
X-ray/cavity and corrected PRAiSE2 products at `0/45/90 deg`.

The scientific boundaries are explicit. Tracer cannot define the observer
X-ray mask. Quantitative cavity energy requires exactly two non-crossing
opposite-side X-ray components, and ambient pressure remains a labelled
tracer-shell proxy. `G-HI` endpoint non-shock observables remain usable, but
shock positions stop at snapshot `47` and centred speed/Mach values at `46`.

The implementation runs the full tranche as one lighter four-case X-ray job
and four independent case-level radio jobs. The split isolates expensive
history caches and makes failure recovery case-specific; it does not reduce
the prespecified science surface.

Local focused validation passed (`52` tests), both wrappers passed shell
syntax checks, and no raw production payload was changed or copied.

Remote preflight then passed for the exact canonical particle sequences, all
selected HDF5 surfaces, the Goal 062 manifests, the reviewed PRAiSE2 source,
staged hashes and syntax, the no-overwrite root, and the `normal` queue.

Submitted jobs, each verified running once, are:

- `787293.kunanyi-ohpc` / `four_xcav` (X-ray/cavity);
- `787294.kunanyi-ohpc` / `c_hi_selrad`;
- `787295.kunanyi-ohpc` / `c_lo_selrad`;
- `787296.kunanyi-ohpc` / `g_hi_selrad`;
- `787297.kunanyi-ohpc` / `g_lo_selrad`.

All five first attempts subsequently failed during launch because the
transient analysis root was on the full scratch allocation. The four radio
stderr logs directly report `Errno 122`; the X-ray common cause is inferred
from its simultaneous launch failure and empty per-case outputs. No science
calculation started. The original evidence is preserved in
`failed_attempt_1/`, including an immutable archive with SHA-256
`266c29b736e6e0d88b991f87daa4b29fbc7f584d918e543cba5462fbe99246ef`.

Both wrappers now place transient analysis products under the enlarged home
allocation. This changes storage placement only: raw inputs, methods, ages,
views, frequencies, and scientific gates are unchanged. Placement regression
tests and local/remote syntax and hash checks passed.

Replacement jobs were submitted and verified running once:

- `787301.kunanyi-ohpc` / `four_xcav_r1`;
- `787302.kunanyi-ohpc` / `c_hi_selr1`;
- `787303.kunanyi-ohpc` / `c_lo_selr1`;
- `787304.kunanyi-ohpc` / `g_hi_selr1`;
- `787305.kunanyi-ohpc` / `g_lo_selr1`.

The PBS stop rule remains active. Do not poll; resume only after Barry reports
a replacement-job completion email or explicitly authorizes a re-check.

An authorized re-check found three radio replacements finished with
`Exit_status=1`: `C-HI` (`787302`), `G-HI` (`787304`), and `G-LO` (`787305`).
Their common error was a missing staged `plutokore.radio.praise` module. This
was downstream of three successfully completed `5001`-output history caches;
the expensive cache work is valid and reusable.

The wrapper now fails fast on the complete runtime dependency surface. A
separate repair stage adds `praise.py` and `raytracing.py` from the same
reviewed plutokore commit, while retaining corrected `praise2.py`. Hash,
syntax, import-API, cache-completion, and no-overwrite checks passed.

Cache-resume jobs `787310` (`C-HI`), `787311` (`G-HI`), and `787312` (`G-LO`)
were submitted and verified running once. X-ray `787301` and C-LO `787303`
were still running at the authorized snapshot; their jobs and stage were not
altered. Do not poll.

Barry subsequently reported C-LO `787303` returned `Exit_status=1`. Its logs
confirmed the identical missing-module failure after successful validation of
the complete `5001`-output manifest. The separate repair stage reused that
cache and recorded resume job `787329` (`c_lo_selr2`), verified running once.
No duplicate was submitted after the orchestration interruption. The X-ray
job remained running at the last authorized snapshot; all four radio resumes
are now under the PBS stop rule.

Status: `submitted_waiting_pbs_completion`.

## X-ray isolated-case repair

PBS `787301.kunanyi-ohpc` / `four_xcav_r1` finished with `Exit_status=1` after
using `126641000kb` of its `128gb` request. The per-case contract makes the
failure boundary explicit: C-HI, C-LO, and G-LO each exited `0` and completed
their selected-age product; G-HI exited `137` after manifest preflight when
the truth extractor was killed. The observed pattern supports aggregate
memory exhaustion from four concurrent full-grid cases, rather than a
scientific-method or source-data failure.

The compact failure archive SHA-256 is
`ed501ae06c2f27a52595c742674a0a26218c3467418444c584b532bfbfa96250`.
The wrapper now supports a default-preserving single-case execution mode.
G-HI-only repair job `787415.kunanyi-ohpc` / `g_hi_xcavr2` was submitted from
a separate no-overwrite stage, verified running once, and left under the PBS
stop rule. The three completed case products remain untouched.

Status: `submitted_waiting_pbs_completion`.

## First radio completions

C-HI `787310.kunanyi-ohpc` and G-HI `787311.kunanyi-ohpc` finished with
`Exit_status=0`. Their corrected-PRAiSE2 products were retrieved and validated
independently. Each contains `50` primary luminosity rows, `150` view rows,
`15` source rows, and `6` particle-source summary rows; luminosity and
effective magnetic field values are finite and positive, particle sources are
causal within numerical tolerance, and stderr is empty.

The byte-preserved retrieval bundle SHA-256 is
`5fa6f428d63665a1345f5f7eeaab7dd9d0ae7a35d856b574cd27acb3291c17b5`.
C-LO, G-LO, and the isolated G-HI X-ray repair remained running at the one
authorized scheduler snapshot. No cross-case synthesis has begun.

Status: `submitted_waiting_pbs_completion`.

## G-LO radio and four-case X-ray completion

G-LO radio `787312.kunanyi-ohpc` and G-HI X-ray repair
`787415.kunanyi-ohpc` finished with `Exit_status=0` and empty stderr. G-LO
passed the same `50/150/15/6` corrected-PRAiSE2 row and scientific-validity
contract as the earlier C-HI and G-HI products.

The repaired G-HI X-ray product passed all `15` selected age/view projection
checks. It was combined without recomputation with the retained successful
C-HI, C-LO, and G-LO products from `787301`. The resulting four-case archive
contains `68` members, covers `60` case-age views, and has SHA-256
`359b9e2fd4d6b87309177adefcab86b34c22a9645fb1c1da8f1deb192a343d3e`.
All projection rows are finite and support-complete. No-component energy rows
remain explicitly nonquantitative.

C-LO radio `787329` remained running at the single authorized scheduler
snapshot and is now the only incomplete Goal 064 product. No polling or
factorial synthesis occurred.

Status: `submitted_waiting_pbs_completion`.

## Final C-LO radio completion

C-LO radio `787329.kunanyi-ohpc` finished with `Exit_status=0`, walltime
`05:40:55`, and empty stderr. Its archive SHA-256 is
`118227510131c1b728fcbf3e9d11b53a9c378a4634c48a52feb582456c345678`.
The product passed the same `50/150/15/6` row, finite-value, causal-source,
selected-coordinate, and corrected-PRAiSE2 provenance contract as the other
three cases.

The complete radio surface contains `200` primary and `600` viewing rows;
the complete X-ray/cavity surface contains `60` case-age-view rows. Goal 064
is now complete and ready for synthesis with Goal 062/063. This closeout did
not start that synthesis or alter raw data.

Decision: `FOUR_CASE_SELECTED_AGE_OBSERVABLE_SURFACE_COMPLETE_SYNTHESIS_READY`.

Status: `complete_product`.
