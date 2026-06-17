# C-HI Final Level 3 Ambient Energy Method Gate

Date: 2026-06-17

## Summary

Goal 008 defines and packages the first Level 3 ambient-energy method gate for
the accepted final 50 Myr `C-HI` endpoint.

Result status:

```text
blocked_remote_postprocessing_access
```

This is a useful blocked method package, not a completed Level 3 energy
measurement. The baseline and final HDF5 inputs exist and expose the fields
needed for thermal and kinetic ambient-energy changes, and a streaming HDF5
extractor is now implemented and locally tested. The full-grid remote
extraction was not run because terminal SSH/SCP to the TPAC jumpbox remained
blocked after Open OnDemand jumpbox enablement. The Open OnDemand web shell was
usable for read-only preflight, but it was not treated as a reliable staging
and retrieval route for a full post-processing job.

The gravitational component is separately blocked:

```text
blocked_missing_potential
```

The accepted HDF5 outputs expose `rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3`,
but not a gravitational potential. This repo does not yet contain a reviewed
potential/profile zero-point convention for Level 3 gravitational energy.

## Product Assets

Asset directory:

```text
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/
```

Files:

- `level3_ambient_energy.csv`: component status table.
- `level3_method_decisions.csv`: method choices, formulas, and blockers.
- `level3_metadata.json`: preflight evidence and comparator values.

New helper scripts:

- `scripts/science/pluto_h5_level3_ambient_extract.py`
- `scripts/science/build_final_level3_ambient_energy.py`

Focused tests:

- `tests/test_pluto_h5_level3_ambient_extract.py`
- `tests/test_final_level3_ambient_energy.py`

## Inputs Verified

Read-only Open OnDemand shell preflight found the baseline and final products:

```text
baseline:
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0

final:
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Both expose:

```text
rho, prs, tr1, vx1, vx2, vx3
shape = 1014 x 960 x 960
```

The final endpoint is the same accepted endpoint used by Goals 003, 005, and
007.

## Method Definition

Ambient mask:

```text
final cells with tr1 <= 5e-3 are ambient
final cells with tr1 > 5e-3 remain Level 2 lobe truth
```

Spatial convention:

```text
whole-grid, side-aware mask:
negative_z = z < 0
positive_z = z >= 0
bipolar_total = both sides
```

Thermal component:

```text
sum((prs_final - prs_baseline) * dV / (gamma - 1)) * unit_energy
```

Kinetic component:

```text
sum(0.5 * (rho_final * v_final^2 - rho_baseline * v_baseline^2) * dV) * unit_energy
```

The unit conversion matches `scripts/science/pluto_h5_truth_extract.c`:

```text
unit_energy = unit_density * unit_velocity^2 * unit_length^3
```

The helper `scripts/science/pluto_h5_level3_ambient_extract.py` streams by
`z` slice and was validated on synthetic HDF5 files for final-tracer masking,
shape rejection, coordinate-axis mismatch rejection, and thermal/kinetic sums.
Before any cell-wise subtraction, it compares baseline and final `X`, `Y`, and
`Z` coordinate axes with `rtol = 0` and `atol = 1e-10 kpc`. The remote preflight
above verified only dataset presence and shape; it did not execute this
coordinate-compatibility check on the full remote pair.

## Comparators

The package carries the accepted comparator scalars:

| Quantity | Value |
| --- | ---: |
| Level 1 bipolar injected energy | `3.1557599999999995e60 erg` |
| Level 2 `tracer > 5e-3` bipolar lobe energy | `1.3881436397447783e60 erg` |
| Goal 005 bipolar `pV` | `6.87805393912703e59 erg` |
| adopted non-relativistic `2.5pV` | `1.7195134847817576e60 erg` |
| literature-comparison `4pV` | `2.751221575650812e60 erg` |

`2.5pV` is carried as the adopted non-relativistic interpretation following
Stas-agent's `Q-012` answer. `4pV` remains the literature comparison.

## What Is Blocked

Thermal and kinetic Level 3 values are blocked by remote post-processing
access, not by local method ambiguity:

- baseline and final HDF5 inputs exist;
- required datasets and shapes are present;
- local extractor tests pass, including the coordinate-axis compatibility
  contract;
- coordinate compatibility has not yet been executed on the full remote pair;
- terminal SSH/SCP through the TPAC jumpbox still returns
  `Permission denied (publickey,password)` after Open OnDemand SSH enablement;
- no PBS job was submitted.

The gravitational Level 3 value is blocked by missing method/input:

- the accepted HDF5 vars do not contain gravitational potential;
- the docs mention environment-table gravitational acceleration, but this goal
  did not read UTAS AGN source checkouts or external environment files outside
  the authorized repo and named existing-output paths;
- a reviewed potential/profile integration and zero-point convention is needed
  before gravitational energy can be compared with Level 1, Level 2, `2.5pV`,
  or `4pV`.

## Recommendation

Do not broaden yet. Stas-agent made Level 3 required before broadening, and
Goal 008 has not produced thermal/kinetic values.

Recommended next goal:

```text
C-HI Level 3 bounded remote extraction closeout
```

That goal should first repair terminal SSH/SCP or approve a reliable Open
OnDemand staging/retrieval route, then run the tested streaming extractor on
the existing baseline/final HDF5 pair. It should package thermal and kinetic
Level 3 rows locally and keep the gravitational component blocked unless Stas
or Patrick provide a reviewed potential/profile convention.
