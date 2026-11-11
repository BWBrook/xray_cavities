# Production spherical energy-budget extractor

Status (11 November): all six turn-15 analysis jobs finished F/0. Aggregate
receipts cover all 51 snapshots in each independent case and all 48 retained
G-HI snapshots (0--47); the separate G-HI/20 emission diagnostic also completed.
Only the C-HI snapshot-1 smoke has the independent scientific review described
here. Full product-hash verification and scientific review remain pending;
physical closure is not established.
See [the completion check](../exchange/logs/2026-11-11-turn15-completion-check.md).
See [the native result and execution record](../exchange/logs/2026-11-05-turn15-native-budgets-and-lineage.md).

Implementation: `scripts/science/extract_spherical_energy_budget.py`
Tests: `tests/test_spherical_energy_budget.py`

Turn 15 extension (5 November): method version 2 also records the global
native lobe pressure integral in the first streaming pass, with resolved
`2.5*sum(pV)` and `4*sum(pV)` and their injected-energy ratios. It uses current
pressure without initial subtraction, includes slow lobe cells outside either
aperture, and is a separate proxy comparison, never an additive fourth ledger
term. Native-proxy qualification is separate from aperture-specific holds.
The R100 and R300 geometry holds are now independent; a larger-aperture hold
must not be copied into the smaller aperture.

`scripts/kunanyi/prepare_spherical_budget_inputs.py` and
`run_spherical_budget_case.py` bind reviewed historical configuration and
atmosphere witnesses, the original production path, live source/configuration
properties and exact stable file identities. Historical executable-to-source
linkage remains separately flagged when not proved. The runner processes one
case serially and checks prior receipts against the freshly validated native
chain before resuming. Its per-snapshot completion receipts bind all analysis
source hashes. `summarize_spherical_energy_budgets.py` reports absent snapshots
and unavailable thresholds explicitly, preserving native and aperture holds.

## Scientific target and scope

The extractor measures the change in stored gas energy inside two
speed-defined apertures in one retained native PLUTO snapshot. It answers:

> How much thermal, kinetic and fixed-potential gravitational energy has
> changed, relative to the actual initial cells, in the saved region enclosed
> by the furthest gas moving at least 100 or 300 km/s?

This is a deterministic diagnostic of each simulation and saved snapshot. It
is not a population estimand, a replicate-based uncertainty estimate, or an
energy-conservation closure test. The aperture changes with time and the
extractor does not measure flux through that moving surface.

The intended production surface is every available scientifically retained
snapshot of `C-HI`, `C-LO`, `G-HI`, and `G-LO`. Actual HDF5 times are used.
The full-history G-HI boundary audit first detects contamination at snapshot 48, so
this extractor rejects G-HI indices 48--50. This is stricter and more explicit
than merely omitting the selected 50-Myr endpoint. The valid selected-age G-HI
surface still ends at 40 Myr.

## Estimand

For threshold \(s\) in 100 and 300 km/s,

\[
R_s(t)=\max_{|\mathbf v_i(t)|\ge s} r_i,
\qquad |\mathbf v|=\sqrt{v_{x1}^2+v_{x2}^2+v_{x3}^2}.
\]

The threshold comparison is inclusive (`>=`). If no cell qualifies, the
radius and budget are unavailable (`null`); they are not reported as zero.

The primary discrete aperture contains every saved physical cell with centre
radius \(r_i\le R_s\). Each selected finite-volume cell has full weight, so
slower gas inside the aperture is included. The raw radius is retained and
the padding is exactly zero: this estimand assigns cells by their centres and
the inclusive radius already contains every radius-defining cell. It does not
claim that every selected cell's corners lie inside a continuous sphere.

For component \(a\), the change is evaluated cell by cell before summation:

\[
\Delta E_a(<R_s,t)=\sum_{r_i\le R_s}
[e_{a,i}(t)-e_{a,i}(0)]V_i.
\]

The terms are:

- thermal: \([p(t)-p(0)]V/(\gamma-1)\), with \(\gamma=5/3\);
- kinetic: \(\tfrac12[\rho(t)|\mathbf v(t)|^2-\rho(0)|\mathbf v(0)|^2]V\);
- gravitational: \([\rho(t)-\rho(0)]\Phi_0(r)V\), using the fixed,
  centre-zero potential integrated from the initial tabulated gravity.

The initial density, pressure and all three initial velocities are read from
the actual t=0 HDF5. No initially static or tracer-free nozzle is assumed.

The same current aperture is partitioned by current full-cell membership:

```text
cocoon: tr1(t) > 1e-3
ambient: tr1(t) <= 1e-3
```

The current mask is applied to each cell's current-minus-initial change. These
are Eulerian current regions, not Lagrangian parcels. The independent cocoon
and ambient sums must reproduce the total within `1e-9` of the larger of the
injected energy and measured component scales; failure aborts extraction.
Tracer values are used as stored. Any current value outside `[0,1]` is counted
and places scientific interpretation on an explicit tracer-quality hold. The
extractor applies no tolerance, clipping or automatic cleanup.

Normalization uses the labelled bipolar powers `2e45 erg/s` for `*-HI` and
`2e43 erg/s` for `*-LO`, multiplied by the actual age and capped at 50 Myr.
The t=0 normalized ratio is undefined, not zero.

## Geometry and coverage diagnostics

The native cell edges define exact finite-volume cell volumes. HDF5
`node_coords` are preferred and cross-checked against `grid.out` when both are
supplied. If node coordinates are absent, `--grid-file` is required. Current
and initial axes and edges must agree exactly.

For each threshold the output reports:

- the raw radius, radius-defining cell, velocity components, tracer value and
  distance of the complete cell from the nearest domain face;
- whether the defining fast cell has any same-threshold neighbour in its
  26-cell neighbourhood (an isolated-outlier flag, not a topology repair);
- whether a sphere of that radius fits inside the domain's inscribed sphere;
  beyond that limit the reported object is explicitly a
  `domain_truncated_spherical_cell_selection`, and scientific qualification is
  held even though the raw cell selection and budget remain available;
- whether it fits inside the box formed by excluding the requested distance
  from all six faces (40 kpc by default); any conflict is a separate
  qualification hold;
- the primary uncut budget, the conditional sphere-intersection-safe-box
  budget, and the cells lost to that cut, including lost cocoon cells;
- cocoon cell/volume coverage and the number of >=100-km/s cells outside each
  aperture;
- a coverage diagnostic outside the aperture but inside the safe box, flagging
  cells with current Mach >=0.05, absolute pressure change >=1%, or absolute
  density change >=1%.

The coverage thresholds never alter the aperture. They expose weak waves or
other disturbed gas that a speed cut can miss. Zero tracer, absence of a
supersonic shock, or a clean radius-defining neighbourhood does not prove the
outer gas is undisturbed.

The safe-box product is conditional. It must not replace the complete
spherical cell selection silently, and any lost cocoon or other jet-affected
gas remains explicit. Neither product measures energy transport across its
surface. The default 40-kpc width is the supervisor's candidate cut, not a
certified safe region; the paired-control interior audit must evaluate it.
Safe-intersection plus excluded cells is independently checked against the
primary aperture for counts and every energy component.

## Execution and qualification states

Successful HDF5 reading and arithmetic are recorded only as
`execution_status: completed_spherical_energy_budget_measurement`. They do not
produce a generic `complete` or `valid` scientific status.

Every measured threshold has `measurement_status: measured` and a separate
`scientific_qualification` object. The extractor never sets `qualified: true`.
It preserves measured budgets while emitting machine-readable holds for:

- external native case/configuration/environment identity not established by
  this extractor;
- any stored tracer value outside `[0,1]`;
- a raw radius that produces a domain-truncated spherical cell selection;
- conflict with the candidate boundary-safe box.

Isolated radius-defining cells, cocoon outside the aperture and disturbed
safe-box cells outside the aperture remain review flags. An absent threshold
has an unavailable measurement, not a zero budget. The R100-minus-R300
difference is retained when both measurements exist, but is labelled a
conditional diagnostic and inherits every hold from both thresholds.

## Provenance and failure policy

The production CLI requires `--input-receipt`. A schema-version-1 receipt
binds the case, snapshot index, timestep names and times, and the exact current
HDF5, t=0 HDF5, environment table, and optional `grid.out`. Every input record
contains:

```json
{
  "path": "/absolute/path",
  "resolved_path": "/resolved/absolute/path",
  "size_bytes": 123,
  "mtime_ns": 123,
  "ctime_ns": 123,
  "device": 1,
  "inode": 2,
  "sha256": "64 lowercase hexadecimal characters"
}
```

The enclosing receipt is:

```json
{
  "schema_version": 1,
  "status": "bound_spherical_budget_inputs",
  "case": "C-HI",
  "snapshot_index": 1,
  "current": {"timestep": "Timestep_1", "time_code": 306.6},
  "initial": {"timestep": "Timestep_0", "time_code": 0.0},
  "inputs": {
    "current_h5": {},
    "initial_h5": {},
    "environment": {},
    "grid_file": {}
  }
}
```

`grid_file` is omitted from both the command and receipt when native node
coordinates suffice. Receipt roles must match the supplied inputs exactly.
The receipt must come from accepted source/migration evidence or a fresh
stable full-hash validation; a source manifest containing paths and times but
no hashes is insufficient.

This binding receipt proves only exact file identity and declared labels. It
does not prove that the declared case used the intended compiled/runtime
configuration or case-appropriate atmosphere. Those semantic identities must
be established by external accepted run/configuration receipts before a
native result can be scientifically qualified. A synthetic or self-authored
binding receipt can exercise the extractor but cannot qualify production.

Metadata are checked before and after both passes. A device-only transition is
accepted only after a matching full SHA-256 with stable metadata; any other
change fails closed. The receipt and extractor source are also hashed and
rechecked. Output is an atomically published JSON receipt and an existing path
is never overwritten.

The failed flux job 876162 and its cancelled dependent native pilot provide no
input qualification. In particular, the G-HI continuation root has no
duplicate `src` directory. A G-HI extraction must bind the accepted split
chain's exact HDF5 files independently; source-tree assumptions from those
failed jobs are not reused.

The separate `configured_case_index_exclusion_gate` means only that the known
G-HI 48--50 exclusion did not fire. It is not general scientific validation.

## Bounded-memory execution

The extractor streams one z slab at a time.

1. Pass 1 reads the current surface to find raw radii, cocoon extent, tracer
   range and radius-defining cells.
2. Pass 2 reads the current and actual t=0 slabs together and accumulates both
   aperture budgets, tracer partitions, safe-box cuts and coverage checks.

Memory is proportional to a handful of x-y slabs, not the full
`1014 x 960 x 960` grid. Each snapshot is independent, so a batch can resume
at the first absent output without overwriting completed receipts. Correctness
comes before throughput; do not run several native reads against the same
storage merely to fill cores.

## Synthetic verification

Run:

```bash
UV_CACHE_DIR=/tmp/xray-spherical-uv-cache \
  uv run pytest -q tests/test_spherical_energy_budget.py
```

The focused suite covers:

- full three-component speed where no single component reaches the threshold;
- unavailable thresholds as null rather than a zero budget;
- actual initial velocity/density/pressure subtraction under current binary
  tracer membership, including strict equality at `tr1 == 1e-3`;
- analytic positive and negative density perturbations under a fixed
  centre-zero linear potential, pinning gravitational sign and scale;
- independent R100/R300 budgets, bipolar injection normalization and partition
  identity;
- safe-box clipping, lost cocoon energy, incomplete domain spheres, isolated
  radius-defining cells and weak outer disturbances;
- explicit unreviewed tracer-quality holds without clipping or tolerance;
- receipt binding, wrong-case and mutated-input rejection, atomic
  no-overwrite, invalid primitives, the G-HI exclusion, and the executable
  one-snapshot CLI.

Passing tests validate the arithmetic and failure policy on synthetic grids.
They do not validate any production snapshot or establish physical closure.

## Smallest production smoke

Use one early, scientifically valid annual snapshot (recommended `C-HI/1`)
on an allocated Kunanyi compute node. Read the native files in place; do not
copy a full HDF5 merely for the smoke. Stage these small code dependencies
from one reviewed repository revision:

```text
scripts/science/extract_spherical_energy_budget.py
scripts/science/measure_q031_fluxes.py
scripts/science/pluto_h5_level3_ambient_extract.py
scripts/science/select_common_age_hdf5.py
scripts/science/snapshot_energy.py
tests/test_spherical_energy_budget.py
```

Also stage or identify the accepted cluster environment table, `grid.out` if
the HDF5 lacks node coordinates, and a new exact input receipt for C-HI/1 and
its C-HI/0 baseline. The receipt must refer to the live compute-node paths and
must bind every supplied role.

After running the focused tests in the staged environment:

```bash
python scripts/science/extract_spherical_energy_budget.py \
  --case C-HI \
  --snapshot-index 1 \
  --current-h5 "$C_HI_OUTPUTS/data.0001.flt.h5" \
  --initial-h5 "$C_HI_OUTPUTS/data.0000.flt.h5" \
  --environment "$C_HI_ROOT/tabulated_cosmo_002003.csv" \
  --grid-file "$C_HI_OUTPUTS/grid.out" \
  --input-receipt "$RECEIPTS/C-HI_0001_spherical_inputs.json" \
  --output "$RESULTS/C-HI_0001_spherical_budget.json"
```

Omit `--grid-file` only if the receipt also omits `grid_file` and the native
HDF5 has complete node coordinates. Execution success means the measurement
status is emitted, both available partition identities pass, and all
geometry/coverage flags are interpretable. The result remains scientifically
held until external semantic source identity and every reported hold are
reviewed. It is not a scientific acceptance of the snapshot or four-case time
series. Batch expansion should occur only after this output is reviewed, using
one fresh output per case/snapshot and preserving all unavailable or conflicted
records.
