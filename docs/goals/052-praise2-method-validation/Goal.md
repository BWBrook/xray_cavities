# Goal 052 — PRAiSE2 high-level method validation

Date opened: 2026-07-29
Status: `complete_local_fail_closed_gate`

## Objective

Apply Patrick-agent's `Q-022` contract to the documented high-level
`plutokore.radio.praise2.praise(...)` particle interface. Determine whether
Goals 050-051 transfer unchanged, require a provenance amendment, or require a
distinct rerun under PRAiSE2.

This goal stops at the first material fail-closed gate. It does not authorize a
cache-scale comparison, production history generation, raytracing, a pinned
plutokore change, or adoption of a production default.

## Pinned implementation

- Callable: `plutokore.radio.praise2.praise`
- Source:
  `/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py`
- Commit: `e80252cf35ff5a06166240e2867d3d485aaf6956`
- Source SHA-256:
  `ad664648040c4330ce124fdde7b739b7cd701759a52569863fc79460895f9668`

The exact cache and selection contracts remain those of Goal 051:

- cache SHA-256:
  `f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30`
- selection SHA-256:
  `35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df`
- selected rows: exactly `4096`, in declared `sample_index` order.

## Required gate

Patrick's contract requires exact provenance and order, documented units and
shapes, deterministic repeat, endpoint-emissivity comparison, and direct
gamma/state, cutoff, non-finite, and fallback agreement.

The public high-level call returns emissivity products but not the gamma
trajectory, cutoff state, or fallback record. Its pinned source also differs
from the Goal 050 stable method in the Larmor-gamma convention, radiative
coefficient, and full-loss recurrence. Those are material method differences,
not metadata differences.

The gate therefore stops at `HOLD` before a cache-scale run. PRAiSE2 is not
promoted, and Goals 050-051 remain immutable historical baseline evidence.

## Local implementation

The local adapter and diagnostic contract are:

- `scripts/science/praise2_method_validation.py`
- `scripts/science/diagnose_praise2_method_validation.py`
- `tests/test_praise2_method_validation.py`
- `tests/test_diagnose_praise2_method_validation.py`

They pin callable provenance, preserve exact cache/selection order, define the
PRAiSE2 unit and loss-code contract, group histories by effective start,
require exact preservation of every history index through PRAiSE2's internal
resampler, disable PRAiSE2's internal linear smoothing, preserve non-finite
endpoint classes, and fail closed when state trajectories are not observable.
The scaffold labels its available lower-level comparator as the raw Goal 049
method. Goal 051's stable branches are not available to this driver until the
Goal 051 archive is retrieved.

## Decision

Decision label:
`PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION`

Goal 050's stable full-loss result cannot be relabelled as a PRAiSE2 result.
A future PRAiSE2 method-value result must be a fresh result under the intended
high-level implementation. Before such a run is worthwhile, the public method
needs an auditable state/cutoff output or an explicitly reviewed
instrumentation path.
