# C-HI Final Production Prove-out Gap Audit

Date: 2026-06-11

## Summary

The first full 50 Myr `C-HI` production run is now a credible anchor for
continued prove-out. It has green endpoint integrity, readable final grid and
particle products, bounded sparse-particle workflows, Level 1 injected-energy
truth, Level 2 tracer-lobe truth, and an accepted sparse PRAiSE-compatible
radio bridge with final tracer-volume coupling.

That is not the same thing as a finished science pipeline. The current project
state does not yet prove the final X-ray path, the final cavity-measurement
protocol, viewing-angle sampling, source-age sampling, Level 3 ambient-medium
energy, beam/instrument treatment, or readiness for the mandatory `C-LO` and
`G-LO` comparison cases.

The recommended next action is a narrow Goal 005: build the final-endpoint
`C-HI` X-ray plus cavity alignment gate at `50 Myr`, `0 deg`, using the already
accepted Level 1/2 truth and Goal 003 volume-coupled radio product as
comparators. It should not launch a new PLUTO production run.

Machine-readable matrix:

```text
docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv
```

## What Goals 001-003 Proved

Goal 001 proved a local contract: `scripts/science/sparse_particle_radio_bridge.py`
can consume a selected-ID keyed external `id,loss_factor` table through
`--loss-table`, while preserving the pressure-history proxy default. The
contract fails fast for missing IDs, duplicate IDs, non-integer IDs,
non-finite values, negative values, and configured-column mistakes.

Goal 002 proved a first real final sparse selected-ID PRAiSE-compatible loss
table for the completed `C-HI` endpoint. It used the sparse final window rather
than a dense all-history particle cache, generated a 20,000-ID table, verified
determinism on the 64-ID smoke subset, and passed the bridge metadata gate:

```text
loss_model_key = external_praise_compatible
matched_selected_ids = 20000
extra_ids = 0
table_rows = 20000
```

Goal 003 proved final endpoint volume coupling for that same sparse bridge. It
extracted Level 1/2 final truth from `data.0051.flt.h5`, selected the final
`tracer > 5e-3` side volumes, and reran the Goal 002 bridge with declared side
volumes:

| Side | Final `tracer > 5e-3` volume (`kpc^3`) |
| --- | ---: |
| negative z | `367123.31815126061` |
| positive z | `373343.26830024854` |
| bipolar total | `740466.58644933475` |

Together, Goals 001-003 prove a narrow but valuable radio/truth bridge: selected
final sparse particles can carry a real PRAiSE-compatible loss table, and their
bridge luminosity scale can be tied to final grid/tracer lobe volumes.

## What The First Full C-HI Run Proves

The final production endpoint itself is healthy as a run product. Job
`697298.kunanyi-ohpc` reached the configured 50 Myr stop with
`Exit_status = 0`, using 64 nodes and 1792 MPI ranks. The final HDF5 and
particle files are present and readable, including:

```text
data.0011.dbl.h5
data.0051.flt.h5
particles.5000.dbl
```

The final grid quick-look showed nonblank density, pressure, tracer, and
jet-axis diagnostics. The default `tracer > 5e-3` extent is large but not
obviously boundary clipped in the quick-look. The endpoint particle summary
showed `196732` particles at 50 Myr with internally consistent field and lobe
summaries.

The bounded sparse-window path is also proven for the final endpoint. It reads
selected particle outputs `4950, 4955, ..., 5000`, avoids the rejected dense
all-history particle cache, and provides a 20,000-ID selected set that is fully
present at the target output.

The restart and output-catalogue discipline is credible. Earlier reduced-grid
and configuration audits proved the restart template, HDF5 output, rank layout,
runtime-stack recording, and output-footprint reporting expectations. The full
endpoint then demonstrated that the 50 Myr production chain could actually
complete.

## What Remains Provisional Or Missing

The final X-ray observable is missing. The XRAiSE grid path is proven on the
aligned 5 Myr smoke target, but no final 50 Myr XRAiSE/GRAiLE X-ray product is
recorded for the endpoint.

The final cavity protocol is proxy-only. The 5 Myr cavity stub establishes a
reproducible ellipsoid plus ambient-shell workflow and returns finite `pV`,
`4pV`, and simple age estimates, but its buoyancy/refill ages use a provisional
hydrostatic proxy and it has not been applied to the final endpoint.

Level 3 ambient-medium energy is not method-locked. Stas' feedback makes this
scientifically important because shocks and gas ahead of tracer-defined lobes
can carry thermal and kinetic energy, but the current repo does not yet define
the final ambient thermal/kinetic/gravitational diagnostic.

The current radio products are green but narrow. They use the final sparse
window, selected particles, and declared lobe volumes, but are still
particle-binned products without beam/instrument treatment or a full grid
radiation-transfer replacement.

Viewing-angle and source-age sampling are not yet satisfied. Existing aligned
products are `0 deg`; the plan requires `0`, `45`, and `90 deg` post-processing
views and a controlled source-age sampling protocol.

The comparison suite is not ready. Step 11 remains mandatory: the core Honours
scope requires at least `C-HI`, `C-LO`, and `G-LO`. The present evidence is
single-case `C-HI` prove-out only.

## Matrix

Status categories:

- `proven`: aligned with the current full `C-HI` endpoint or an accepted gate.
- `green_narrow`: works for a bounded contract but should not be widened by
  implication.
- `proxy_only`: mechanics exist only as smoke/proxy evidence.
- `missing`: the gate has not been executed for the required scope.
- `needs_decision`: the method or strategic choice must be settled first.

| Component | Status | Nearest next action |
| --- | --- | --- |
| Meeting 2 alignment | `proven` | Keep Meeting 2 as the working plan and use this audit to correct the immediate next action. |
| Honours plan gate alignment | `green_narrow` | Map each next goal to gates A-F and preserve Step 11 as mandatory. |
| final endpoint integrity | `proven` | Use the 50 Myr endpoint as the anchor for final post-processing prove-out. |
| restart and output catalogue | `proven` | Keep catalogue/provenance requirements in future run wrappers and reports. |
| early diagnostic coverage | `proven` | Treat early diagnostics as historical prove-out evidence. |
| final quick-look health | `proven` | Promote endpoint health into final aligned X-ray/cavity/truth/radio post-processing. |
| endpoint particle state | `proven` | Use endpoint particle state as the sanity anchor for sparse-window products. |
| sparse particle window | `proven` | Keep bounded sparse-window workflows and avoid dense all-history caches. |
| Level 1 injected energy | `proven` | Carry Level 1 as the baseline truth comparator. |
| Level 2 tracer-lobe truth | `proven` | Use final `tracer > 5e-3` side volumes and energies downstream. |
| Level 3 ambient energy | `needs_decision` | Define the ambient thermal/kinetic/gravitational method before implementation. |
| final X-ray observable | `missing` | Build a final-endpoint XRAiSE/GRAiLE X-ray product for `0 deg`. |
| final cavity protocol | `proxy_only` | Apply or refine the cavity protocol on the final endpoint after final X-ray generation. |
| radio sparse PRAiSE loss table | `green_narrow` | Retain the selected-ID loss-table contract unless a reviewed goal widens it. |
| radio volume coupling | `green_narrow` | Use Goal 003 as a scalar/radio continuity product with caveats explicit. |
| beam or instrument model | `missing` | Defer until the final endpoint X-ray/cavity/radio path is stable. |
| viewing-angle sampling | `missing` | After `0 deg` is stable, repeat the fixed protocol for `45` and `90 deg`. |
| source-age sampling | `missing` | Define a compact source-age sampling set after the endpoint path is proven. |
| comparison-suite readiness | `missing` | Do not launch `C-LO` or `G-LO` until the `C-HI` final protocol is fixed and reviewed. |
| next major run readiness | `needs_decision` | Use Goal 005 to close the final X-ray/cavity alignment gap before broader production. |

## Recommended Goal 005

Recommended shape:

```text
C-HI final endpoint X-ray/cavity alignment gate
```

Goal 005 should produce one compact, reviewable final-endpoint alignment
product for `C-HI` at `50 Myr`, starting with the `0 deg` view:

- run or package the final `C-HI` XRAiSE/GRAiLE grid X-ray product using the
  completed endpoint;
- apply the existing cavity protocol or a minimally refined version to that
  final X-ray/tracer target;
- report cavity `pV`, `4pV`, and age estimates with their assumptions;
- compare those quantities against accepted Level 1 injected energy, Level 2
  tracer-lobe energy, and the Goal 003 volume-coupled radio scalars;
- keep beam/instrument treatment, `45/90 deg` views, source-age sampling,
  Level 3 ambient energy, and new production runs out of scope unless the
  orchestrator explicitly widens the goal.

This is the right next gate because it attacks the biggest missing link in the
Meeting 2 workflow without changing run physics or prematurely opening new
simulation cases.

## Questions Or Decisions

For Barry:

- Should Goal 005 be allowed to use bounded Kunanyi post-processing for the
  final X-ray/cavity product, or should it first be a local-only protocol and
  wrapper review?
- Should the first Goal 005 view remain strictly `0 deg`, with `45/90 deg`
  deferred until after the final endpoint protocol is accepted?

For Stas:

- Is the current ellipsoid plus ambient-shell cavity protocol acceptable as
  the first final endpoint measurement, or should the pressure/age estimator
  be revised before applying it at 50 Myr?
- Which Level 3 ambient-energy definition should be treated as the first
  method target: thermal only, thermal plus kinetic, or full
  thermal/kinetic/gravitational partition?

For Patrick:

- Is the current XRAiSE/GRAiLE grid path sufficient for the first final
  endpoint X-ray product, or should the port be adjusted before the 50 Myr
  extraction?
- Are there any particle/radio runtime constraints that should be locked
  before using the Goal 003 volume-coupled radio scalars beside the X-ray and
  cavity quantities?
