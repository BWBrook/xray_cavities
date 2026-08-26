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
