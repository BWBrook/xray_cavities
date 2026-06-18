# C-HI Final Level 3 Remote Extraction Closeout

Date: 2026-06-18

## Summary

Goal 009 completes the bounded remote thermal/kinetic Level 3 ambient-energy
extraction for the accepted final 50 Myr `C-HI`, `0 deg` endpoint.

Thermal/kinetic status:

```text
green_level3_thermal_kinetic_closeout
```

Overall Level 3 status:

```text
partial_green_with_gravitational_blocker
```

The remote PBS job completed with `Exit_status = 0`, produced finite
side-aware ambient thermal and kinetic energy changes, and the compact outputs
were retrieved locally. Gravitational Level 3 remains blocked because no
reviewed potential/profile zero-point convention is available inside the
authorized evidence.

## Product Assets

Asset directory:

```text
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/
```

Key files:

- `level3_extractor_output.csv`: raw remote extractor output.
- `level3_ambient_energy.csv`: packaged component table with comparator ratios.
- `level3_method_decisions.csv`: method and contract audit table.
- `level3_metadata.json`: provenance, remote job status, and checksums.
- `remote_logs/c_hi_final_level3_ambient_energy.out`: remote stdout.
- `remote_logs/c_hi_final_level3_ambient_energy.err`: remote stderr, zero bytes.
- `remote_logs/final_level3_ambient_energy_2026-06-18.tar.gz`: compact remote archive.

Tooling:

- `scripts/science/pluto_h5_level3_ambient_extract.py`
- `scripts/science/build_final_level3_remote_extraction_closeout.py`
- `scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs`

## Remote Execution

Job:

```text
699326.kunanyi-ohpc
Job_Name = c_hi_l3amb
Exit_status = 0
resources_used.walltime = 00:02:39
resources_used.cput = 00:01:12
resources_used.mem = 150096kb
```

Inputs:

```text
baseline:
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0

final:
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

The remote job preflight confirmed both HDF5 files expose `rho`, `prs`, `tr1`,
`vx1`, `vx2`, and `vx3` with shape `1014 x 960 x 960`.

The coordinate-compatibility contract was executed by the remote extractor. The
evidence is the SHA-matched extractor, successful `Exit_status = 0`, and remote
stdout reaching `level3_extractor_validation=passed`; the extractor
unconditionally compares baseline/final `X`, `Y`, and `Z` coordinate axes with
`rtol = 0` and `atol = 1e-10 kpc` before streaming any field subtraction.

## Method

Ambient mask:

```text
final cells with tr1 <= 5e-3 are ambient
final cells with tr1 > 5e-3 remain Level 2 lobe truth
```

Components:

```text
thermal = sum((prs_final - prs_baseline) * dV / (gamma - 1)) * unit_energy
kinetic = sum(0.5 * (rho_final*v_final^2 - rho_baseline*v_baseline^2) * dV) * unit_energy
```

The calculation is whole-grid and side-aware, split into `negative_z`,
`positive_z`, and `bipolar_total`.

## Results

| side | thermal delta (erg) | kinetic delta (erg) | thermal + kinetic (erg) |
| --- | ---: | ---: | ---: |
| negative_z | `1.1298792056503806e60` | `2.698123371116687e59` | `1.3996915427620493e60` |
| positive_z | `1.1295262689975807e60` | `2.7244593345855443e59` | `1.401972202456135e60` |
| bipolar_total | `2.259405474647962e60` | `5.422582705702232e59` | `2.8016637452181852e60` |

Bipolar thermal-plus-kinetic comparator ratios:

| comparator | ratio |
| --- | ---: |
| Level 1 bipolar injected energy | `0.887793667838551` |
| Level 2 `tracer > 5e-3` bipolar lobe energy | `2.018280864459599` |
| Goal 005 bipolar `pV` | `4.073337851104109` |
| adopted non-relativistic `2.5pV` | `1.6293351404416438` |
| literature-comparison `4pV` | `1.0183344627760273` |

The side totals are nearly balanced: `1.3996915427620493e60 erg` for
negative-z and `1.401972202456135e60 erg` for positive-z.

## Caveats

- This is a Level 3 ambient thermal/kinetic method closeout for the accepted
  `C-HI` final endpoint, not a final publication-ready observable product.
- The ambient mask is tied to the existing `tr1 <= 5e-3` convention and does
  not replace X-ray/cavity topology review.
- Gravitational Level 3 remains `blocked_missing_potential`; no gravitational
  result should be inferred from this package.
- This goal does not broaden to `45/90 deg`, source-age sampling, `C-LO`, or
  `G-LO`, and it does not produce final radio observables.

## Recommendation

Treat thermal/kinetic Level 3 for the final `C-HI` endpoint as reviewable and
ready for Stas/Patrick method interpretation. Keep the gravitational component
blocked until a reviewed potential/profile convention exists. The next project
decision is whether this thermal/kinetic closeout is sufficient to unblock the
first controlled broadening goal, or whether reviewers want a gravitational
convention first.
