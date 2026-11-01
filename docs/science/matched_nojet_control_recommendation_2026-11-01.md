# Matched-production no-jet control: decision and cost basis

This is a recommendation, not a new simulation authorisation. Barry requested
an assessment against the existing-control audit and the retained-output
analyses on 1 November 2026.

## Recommendation

Prepare the exact cluster control specification, but defer a full run until
the existing-control audit and four-case flux results have been reviewed.
Those results can show whether a regional energy budget already answers the
immediate conservation question and what a new control needs to measure.
The first native-emission results will inform the value of an evolved
background for X-ray interpretation. Waiting for adoption of a replacement
cavity detector is not necessary. If production-background drift remains
material to the intended energy/coupling claim, run cluster first; add group
if the comparative claim requires equivalent controls.

Match the production atmosphere, stretched grid, domain, gravity, outflow
boundaries, solver, units, numerical settings and, for the strictest numerical
comparison, MPI decomposition. Disable both initialized nozzle material and
subsequent injection; omit particle histories. Record sufficiently frequent
integrated storage and numerical boundary/source terms, if accessible, rather
than relying only on sparsely saved three-dimensional fields.

A control would measure the atmosphere's evolution on the actual production
grid without jets and permit same-cell control-relative energy comparisons.
It could also supply an evolved X-ray background. It would not by itself
measure discrete jet delivery, recover missing historical numerical face
fluxes, demonstrate resolution convergence or make jet/background interaction
an additive correction. Different CFL timesteps can also prevent bitwise
agreement outside a jet's causal region. Keep the original budgets alongside
control-relative results; reproducibility of identical runs does not prove an
exact cellwise counterfactual after changing their physics.

## Why the existing controls are insufficient

The retrieved executed configurations, bound to historical archive SHA-256
`adb099cd1557b192d23f48b6d5a1976225a607ebce9df7c2854b66d44a125c80`, confirm
reflective boundaries on all six faces. Production uses outflow boundaries.
The controls therefore cannot test the specific inflow mechanism suspected
in the production cluster atmosphere. They also use a uniform 1-kpc grid,
where production has 0.05-kpc central spacing and stretched outer cells.
A stable reflective coarse run would be useful evidence about that setup,
but would not establish stability of production.

## Measured accounting and transparent extrapolation

The May-8 controls used 28 ranks for 48:57 (cluster) and 45:22 (group), with
147 and 111 steps to 50 Myr, respectively. Reported memory was about 24 GB;
each retained six approximately 5.37-GiB double snapshots. The cell counts
are 80,000,000 versus 934,502,400 in production, a factor of 11.68128. The
minimum spacing changes by a further factor of 20.

A simple cell-step estimate multiplies measured walltime × 28 ranks ×
11.68128 × 20:

| Atmosphere | Estimated allocated core-hours | Ideal walltime, 448 ranks | Ideal walltime, 1,792 ranks |
| --- | ---: | ---: | ---: |
| Cluster | 5,337 | 11.9 h | 3.0 h |
| Group | 4,946 | 11.0 h | 2.8 h |

These are planning estimates, not benchmarks. They assume similar atmospheric
signal speeds and per-cell-step throughput. Startup timesteps differ markedly
(the coarse first timestep was 3.066 code units versus production `1e-5`),
and stretched-grid CFL behaviour, build, MPI scaling and filesystem writes
can change the result. The 448-rank option changes the original production
decomposition; the 1,792-rank column is the ideal same-allocation projection.
A short matched-grid no-jet pilot should measure steady timestep, cell-step
throughput, peak memory and snapshot-write time before a full allocation.
Linear memory scaling gives approximately 273 GiB aggregate, also an estimate.

For context, C-HI and C-LO production consumed 58,241 and 57,016 allocated
core-hours (1,792 CPUs × 32:30:03 and 31:49:01). Their reported PBS CPU times
do not count the complete allocation reliably, so these comparisons use
allocated CPUs × walltime consistently.

## Storage per atmosphere

Using the existing production fluid-field and coordinate byte contract:

| Retention | Uncompressed bytes, approximate |
| --- | ---: |
| Six double snapshots, 0/10/20/30/40/50 Myr | 404 GB / 0.367 TiB |
| Eleven double snapshots, every 5 Myr | 741 GB / 0.673 TiB |
| Production fluid cadence, 51 float + 11 double | 3.03 TB / 2.756 TiB |

No particle histories are needed. Allow additional space for working files
and any copy/compression overlap. No-jet compression ratios are not measured
and should not be inferred from the jet runs. Prefer frequent compact
integrated diagnostics plus selected full snapshots unless denser maps serve
a stated scientific purpose.

## Sources and coordination

- `docs/exchange/logs/2026-05-08-kunanyi-stewart-environment-gates.md`:
  measured coarse-control accounting and step counts.
- `docs/science/assets/nojet_control_stocktake_2026-11-01/executed_controls/`:
  actual configurations and logs retrieved on 1 November.
- `docs/science/assets/c_hi_configuration_lock_2026-05-08/config/pluto.ini`:
  production grid, CFL and boundary contract.
- `docs/science/assets/cluster_full_history_production_2026-08-17/`:
  launch contract and C-HI/C-LO final scheduler accounting.
- `docs/science/assets/four_case_preproduction_readiness_2026-08-13/uncompressed_storage_forecast.csv`:
  production storage contract.
- `docs/science/q031_boundary_hypothesis_2026-10-31.md`:
  reconstructed-boundary and nozzle limitations.

Claude revised his earlier preference for a cluster matched-grid control to
**defer** in discussion 29, message 2644, pending radial mass and face-flux
measurements. That sequencing agrees with the recommendation here. His
stronger claim that the existing analytical correction already establishes
whole-grid closure is not adopted: the retained G-LO smoke still shows an
8.22% first-interval excess under the outer-active trapezoid convention and
large startup-quadrature ambiguity at the nozzle. Four-case measurements
remain pending. Codex requested his response to the newly confirmed reflective
boundary mismatch and delivered Q-032 results (messages 2781–2789); that fresh
response has not yet arrived. Agreement on sequencing is not validation of
the boundary mechanism or control adequacy.
