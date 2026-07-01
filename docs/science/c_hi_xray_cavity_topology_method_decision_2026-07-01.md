# C-HI X-ray/Cavity Topology Method Decision

Date: 2026-07-01

Status: `complete_local_method_decision_package`

Decision label: `TRACER_PROXY_OK_HYBRID_XRAY_TOPOLOGY_METHOD_NEXT`

## Scope

This local-only decision package reviews the current `C-HI` X-ray/cavity
topology evidence after the late-age axis gate. It uses existing accepted
assets only. It does not rerun XRAiSE, PLUTO, PRAiSE, radio, cavity
extraction, HDF5 post-processing, or remote jobs, and it does not alter
accepted Goal 005/016/017/019/020/021/022 assets.

The decision question is narrower than publication readiness: whether the
current tracer-defined side ellipsoids remain adequate as a review/prove-out
proxy, whether they are sufficient as a final observational X-ray cavity
topology method, and what the next method step should be.

## Evidence Base

Machine-readable assets live in:

`docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/`

Key files:

- `topology_evidence_register.csv`
- `method_option_matrix.csv`
- `go_no_go_criteria.csv`
- `next_step_recommendation.csv`
- `topology_method_decision_metadata.json`

The evidence register draws from:

- Goal 005 final endpoint X-ray/cavity alignment and side-aware tracer
  ellipsoids.
- Goal 007 observational-product readiness package and Patrick-agent review
  context.
- Goals 014/015/016/017 projection diagnostic, bin-refinement, refined
  projection rerun, and refined viewing-angle consolidation.
- Goals 021/022 late-age surface and decision gate.
- Goal 006 method-review energy convention context.
- Goal 009 Level 3 ambient-energy closeout context.

## Findings

The current tracer-defined side ellipsoids are adequate as a reproducible
prove-out and provenance proxy. They are finite, side-aware, map cleanly back
to the accepted `tracer > 5e-3` Level 2 lobe volumes, and provide stable scalar
comparators for `pV`, adopted `2.5pV`, and `4pV` reporting.

They should not be frozen as the final observational X-ray cavity topology
method. The overlays are tracer-defined 3D extents rather than X-ray-fitted
cavity masks. Goal 007 made the X-ray context reviewable, and Patrick-agent
accepted that visual product as product-adequate, but the same review context
read the structure as a connected envelope or single connected lobe requiring
X-ray-based fit confirmation before it becomes a fitted observational-cavity
result.

The historical `90deg` striping concern is no longer the leading topology
caveat. Goal 014 diagnosed that feature as a projection/bin occupancy issue,
and Goals 015/016 fixed the nonzero-view empty-column failure with
`edge_overlap_uniform_cell_projection` while conserving raw/corrected X-ray
sums to roundoff. Future nonzero-view X-ray products should continue to use
that refined projection method.

Goal 022 shows that the late `C-HI` source-age surface is sufficient for now:
outputs `46/48/49/50/51` converge smoothly toward the endpoint across
`0/45/90deg`, with clean support diagnostics. Additional late-age scalar
sampling is not the main next move unless a reviewer identifies a specific
interpretive gap.

## Method Options

The option matrix ranks a hybrid tracer-seeded, X-ray-constrained method as
the next local method step. This route keeps the reproducible side labels and
Level 2 comparability of the tracer proxy, while requiring an explicit X-ray
topology classification and deterministic cavity-mask evidence before any
accepted product is touched.

The current tracer ellipsoids should be retained as a baseline proxy and
fallback comparator. A connected-envelope or single-system treatment should be
tested as an explicit topology branch, not silently adopted as a replacement
for side-aware reporting. A pure residual-threshold mask is promising but
needs a deterministic local protocol before it can drive science products.

Deferring topology work is not recommended: after projection repair and
late-age scalar stabilization, the connected-envelope/X-ray-topology caveat is
now the leading method gap.

## Go/No-Go Criteria

Any future method implementation or product rerun should satisfy these gates:

- Accepted assets remain read-only provenance; new outputs live in a dated
  method-specific bundle.
- The first method pass is local-only and uses existing compact arrays and/or
  synthetic fixtures.
- The method records both side-aware tracer-proxy labels and a connected
  envelope/single-system classification where applicable.
- X-ray mask rules are deterministic, parameterized, and auditable, with
  thresholds or morphology choices recorded in metadata.
- `pV`, adopted `2.5pV`, `4pV`, one-sided/bipolar labels, and the Level 3
  gravity blocker remain explicit.
- No bounded existing-output rerun occurs until a local method gate passes and
  X-ray Cavities explicitly authorizes that rerun.

## Recommendation

Recommended next goal shape:

`local_hybrid_topology_method_design_and_synthetic_gate`

The next goal should design and locally gate a hybrid tracer-seeded,
X-ray-constrained cavity topology protocol using existing compact products and
synthetic/local fixtures. It should produce machine-readable topology
classification, mask/protocol metadata, and clear pass/fail criteria. It
should not launch remote compute or overwrite accepted products.

If that local gate passes, a later goal can consider a bounded existing-output
rerun or repackaging of the final `C-HI` endpoint under an explicit no-overwrite
policy. If it fails, the tracer-defined ellipsoid proxy remains available for
review/provenance use, but should remain labelled as a proxy rather than an
X-ray-fitted observational cavity method.

## Active Caveats

- This is not a publication-ready observable product.
- Connected-envelope versus two-side-cavity topology remains unresolved for
  observational fitting.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
- This package authorizes no remote work, HDF5/XRAiSE rerun, accepted-asset
  overwrite, comparison-case broadening, or scientific-default change.
