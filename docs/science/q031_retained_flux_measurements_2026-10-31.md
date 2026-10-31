# Q-031 retained-output boundary and nozzle measurements

Barry authorised these measurements and safe migration resumption in Codex chat
on 31 October 2026. This tranche post-processes retained outputs; it starts no
new PLUTO simulation. Q-031 closure remains pending the numerical results.

## Measurement

`scripts/science/measure_q031_fluxes.py` integrates signed outward mass and
energy flux over all six domain faces. The energy flux is
`rho * v_normal * (gamma*p/((gamma-1)*rho) + v^2/2 + phi)`.
The potential uses the accepted fixed initial-atmosphere convention. Storage
contains thermal, kinetic and potential energy. Exact HDF5 node coordinates
set volumes, face areas and interpolation distances; legacy centre-derived
volumes are emitted only for reconciliation.

Three closed cuboids enclose the spherical overwrite region, padded by 1, 2
and 4 cells. Their storage change plus time-integrated outward flux estimates
net source delivery, including injection, overwrite removal and pressure work.
Compare this against whole-domain storage change plus boundary flux. Cumulative
outer-cell-layer storage changes locate the boundary contribution spatially.
The source geometry, stationary injector, ideal HD physics and absence of
additional active energy terms are checked against retained source files.

The preferred outer-face reconstruction is the outer active-cell value for the
copied outflow boundary. Linear extrapolation is a sensitivity scenario;
nozzle surfaces use centred and donor-cell reconstructions. Left, trapezoid
and right temporal quadratures expose saved-cadence sensitivity. Their spread
is not a confidence interval. Outputs stream one z slab at a time and preserve
per-snapshot checkpoints tied to input identity and implementation hashes.
The storage scan caches the outer two active planes on each face, avoiding
repeated strided reads from contiguous HDF5 datasets. The cache occupies
437.7 MiB on the G-LO grid and preserves whole-face summation order; direct
and cached synthetic flux rows agree exactly.

## Interpretation limits

These reconstructed fluxes are not the solver's integrated Riemann fluxes.
Closure requires inspecting time quadrature, face reconstruction and nozzle
padding, as well as the independent whole-domain/nozzle balance. The initial
saved state already contains the nozzle, so cumulative source delivery excludes
its instantaneous initial overwrite. Live source hashes record what was
inspected; historical binary identity still requires the production receipts.

G-HI uses the accepted original history before index 10 and the home
continuation thereafter, following the existing validated lineage in
`g_hi_full_history_production_2026-08-20.md`. Late boundary-contaminated G-HI
states remain diagnostic. The spherical-aperture and existing no-jet audits
remain separate requested components of Q-031; this tranche does not close them.

## Validation and execution

Independent formula review checked signs, units, stretched-grid geometry,
array ordering and source-volume interpretation. Analytic tests cover uniform
closed-surface cancellation, component fluxes, nonuniform interpolation,
nozzle padding, time quadrature, provenance drift and resumable outputs.

Remote smoke `870316.kunanyi-ohpc` passed ten synthetic tests, then stopped
because the initial validator rejected an explicit `THERMAL_CONDUCTION=NO`.
The correction accepts a single explicit `NO` or the default; it still rejects
active or duplicate definitions. The failed run is retained as provenance.
Execution receipts and the subsequent launch state are recorded in
`docs/exchange/logs/2026-10-31-flux-and-migration-resume.md`.
