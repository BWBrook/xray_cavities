# Whole-grid energy closure and tracer partition

Status: Q-031 selected-age compact comparison complete; physical discrepancy
diagnosis and annual-snapshot review remain open to Barry-codex.
This note clarifies the first energy test for the next Q-030 manuscript iteration.

## Scope and setup

- Cases: C-HI, C-LO, G-HI and G-LO; cluster/group crossed with high/low power.
- Bipolar injected powers: `2e45 erg/s` (HI) and `2e43 erg/s` (LO).
- Grid: `960 x 960 x 1014`, stretched Cartesian; physical domain
  `+/-200 kpc` in x/y and `+/-250 kpc` in z; central cells `0.05 kpc`.
- Gas: `gamma=5/3`; fixed initial-atmosphere potential
  `Phi_0(r) = integral_0^r |g_0(r')| dr'`.
- Use actual snapshot times and all boundary-valid available annual snapshots.
  Keep G-HI boundary-contaminated outputs excluded from physical conclusions.
  Include every physical grid cell in each retained snapshot, including the
  outer atmosphere; omit only solver ghost cells.

## First: total energy change against injection

For physical energy densities in each cell, calculate

```text
u_i(t) = p_i(t) / (gamma - 1)
k_i(t) = 0.5 * rho_i(t) * |v_i(t)|^2
w_i(t) = rho_i(t) * Phi_0(r_i)

Delta E_q,grid(t) = sum_i [q_i(t) - q_i(0)] V_i,  q = u, k, w
Delta E_grid(t) = Delta E_u,grid + Delta E_k,grid + Delta E_w,grid
E_inj(t) = Q_bipolar * t
R(t) = E_inj(t) - Delta E_grid(t)
```

This is the whole-grid `E(t)-E(0)` test. Evaluate same-cell differences before
summation to reduce cancellation against a large background, and retain the
separate absolute initial and current sums for inspection. No tracer, shock,
entropy, Mach, bilateral-front, cavity-topology or emissivity selection enters
this first calculation. Do not substitute enthalpy for total physical energy.

The intended atmosphere is initially at rest, so initial kinetic energy
should vanish outside any initial nozzle. Its gravitational energy is not
zero under the adopted fixed potential, even at rest. Q-029 also found an
initial nozzle/tracer region in the retained files. Therefore inspect and
subtract the actual initial thermal, kinetic and gravitational fields; do not
assume a purely thermal total baseline. Report gravitational energy as its
change, using the same potential at both times.

Plot and report the comparison before requiring a shock model, boundary-flux
calculation or resolution-matched no-jet control. These may help explain a
residual, but are not prerequisites for displaying the requested basic test.
If it disagrees with injection, first inspect normalization, physical units,
cell volumes, the initial snapshot, potential convention and source accounting.
Then distinguish measured boundary transport or background evolution from
unmeasured explanations. The reported C-LO excess of 6--24 times injection
is a whole-grid issue and is not explained by failure to detect a shock.

## Second: partition the same changes by tracer

Use current binary cocoon membership and its exact complement:

```text
I_i(t) = 1 when tr1_i(t) > 1e-3, otherwise 0
Delta E_q,cocoon(t) = sum_i I_i(t) * [q_i(t) - q_i(0)] V_i
Delta E_q,ambient(t) = sum_i (1-I_i(t)) * [q_i(t) - q_i(0)] V_i
Delta E_q,cocoon + Delta E_q,ambient = Delta E_q,grid
```

Each selected cell has full weight. This is Q-029's complementary
current-region change, not its absolute-lobe/ambient-allocation convention.
Label current-region changes and absolute lobe energies separately. These
are spatial regions, not Lagrangian parcels; changes can be negative.
Report all three components and their totals for both regions, including
C-LO at late times. Show their ratios to injected energy without forcing a
sum of one or interpreting an unexplained residual as cocoon energy.

The numerical identity between the two partitions and the independently
summed grid change is a bookkeeping check. A tolerance of `1e-9 E_inj`
on that identity is not a tolerance on `R(t)` and does not establish physical
energy closure. At t=0, report absolute baselines; injection-normalized ratios
are undefined. Do not add enthalpy or the shock-region subset to this ledger.

## C-LO and sound waves

Stas expects low-power jets in the dense cluster atmosphere to generate
primarily sound waves, especially at late times. This is a physical expectation
to test, not a demonstrated mode decomposition. Failure of the bilateral
supersonic shock criterion restricts that optional shock diagnostic; it does
not invalidate whole-grid or tracer-partitioned energetics.

The setup has no explicit physical viscosity. Damping of resolved smooth
sound waves is numerical and must not be presented as modelled physical
viscous heating. Energy carried by waves still contributes to the full-grid
thermal, kinetic and gravitational changes. Numerical dissipation can transfer
wave energy between components; it does not by itself explain excess total
energy. Shock-specific and irreversible-heating estimates are later diagnostics.

## Requested return

Reuse the existing census and Q-029 compact ledgers where they contain the
required terms; identify missing quantities before any new raw-data work.
Return the all-grid component/total curves overlaid with injection, the signed
closure residual, then cocoon/ambient component and total curves with explicit
initial-state and partition definitions. Include the run setup and validity
range in the summary. Retain the uncorrected grid comparison if a later
background or boundary correction is proposed.

Open the first physical-energetics Results subsection with this audit, ahead
of enthalpy and optional shock interpretation. Replace the ambiguous numerical
closure sentence with wording that explicitly distinguishes a successful
partition identity from agreement with injected energy.

## Direct comparison completed on 2026-10-21

Stas-agent rechecked the 19 accepted selected-age records in Q-029's
`remote_analysis/{case}/native_energy_selected_age.csv`. These contain
independently integrated whole-grid changes as well as absolute current and
initial sums. The native summation includes all 934,502,400 physical cells
and is performed before the separate shock-mask integration in
`scripts/science/build_selected_age_native_shock.py`.

The measured ratio is `Delta E_grid / E_inj`; unity would mean agreement
with the nominal injected energy before boundary/source corrections:

| Case | ~10 Myr | ~20 Myr | ~30 Myr | ~40 Myr | 50 Myr |
| --- | ---: | ---: | ---: | ---: | ---: |
| C-HI | 1.1444 | 1.1872 | 1.2204 | 1.2498 | 1.2785 |
| C-LO | 6.0211 | 10.4577 | 14.9010 | 19.3937 | 23.9673 |
| G-HI | 1.0772 | 1.0766 | 1.0820 | 1.0828 | excluded |
| G-LO | 1.2270 | 1.3199 | 1.4167 | 1.5007 | 1.5771 |

The discrepancy exists in all four cases, not just C-LO. C-HI is 14--28%
above injection, G-HI about 8%, G-LO 23--58%, and C-LO 6--24 times injection.
At C-LO/50, the normalized components are thermal `12.2314`, kinetic
`0.2691`, and gravitational `11.4668`. The measured change is
`7.56351e59 erg`, compared with `3.15576e58 erg` injected. The large excess
does not depend on shock selection or on the tracer partition.

Checks on the compact records confirm:

- Nominal injection agrees with bipolar power times actual active duration
  (365.25 days/year, injection capped at 50 Myr).
- Absolute current-minus-initial component sums reproduce the independently
  accumulated cell-wise changes within `6.12e-12 E_inj`.
- Cocoon plus ambient regional changes reproduce the whole-grid changes
  within `2.30e-14 E_inj`; both hemispheres sum consistently.
- Whole-grid totals are identical across all four stored tracer partitions.
- Stored initial component energies are constant across snapshots in each case.

These checks establish that the discrepancy is present in the stored whole-grid
accounting. They do not independently verify the raw HDF5 primitive-to-energy
conversion, the realised nozzle power, gravitational source update, or boundary
transport. Those are possible audit targets, not established explanations.
No new simulation or raw HDF5 read was performed. Only the selected ages are
verified here; the full annual extension remains to be reviewed.

Reproduce with `python scripts/science/build_whole_grid_energy_check.py`
(Matplotlib is required for the figures). Products:

- `assets/whole_grid_energy_closure_2026-10-21/whole_grid_energy_comparison.csv`
- `assets/whole_grid_energy_closure_2026-10-21/whole_grid_energy_ratios.png`
- `assets/whole_grid_energy_closure_2026-10-21/whole_grid_energy_absolute.png`
- `assets/whole_grid_energy_closure_2026-10-21/validation_summary.json`

The CSV retains the absolute initial/current component sums, cell-wise
differences, cocoon/ambient regional components, injection and signed closure
residual. The JSON records source hashes and checks. Q-031 remains open to
diagnose the physical discrepancy and update the scientific interpretation.
