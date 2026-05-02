# 2026-05-02 Three-Case Science Package

## Summary

The next science plan has been implemented as a repo-tracked launch package.
This is a packaging and gating step, not a production run.

New files:

- `docs/science/three_case_spec.md`
- `docs/science/asset_inventory_2026-05-02.md`
- `scripts/science/render_three_case_configs.py`
- `scripts/science/inspect_tabulated_environment.py`
- `scripts/kunanyi/jet_setup_production_template.pbs`

Updated files:

- `README.md`
- `docs/kunanyi_setup.md`
- `docs/exchange/current_status.md`

## Locked Science Spec

The frozen cases are:

| Case ID | Environment | Jet power | Jet speed | Purpose |
| --- | --- | ---: | ---: | --- |
| `C-HI` | Stewart cluster | `1e45 erg/s` (`10^38 W`) | `0.1 c` | first validation case |
| `C-LO` | Stewart cluster | `1e43 erg/s` (`10^36 W`) | `0.1 c` | baseline science anchor |
| `G-LO` | Stewart group | `1e43 erg/s` (`10^36 W`) | `0.1 c` | environment-dependence case |

Shared defaults:

- HD
- centered launch
- `JET_RELATIVISTIC_DENSITY = NO`
- `JET_OA_PRIMARY = 15.0`
- `JET_OA_SECONDARY = 15.0`
- `JET_END_TIME = 300.0`
- `JET_ACTIVE_TIME = 300.0`
- particles staged after the particle-free `C-HI` rehearsal

Sampling protocol:

- snapshots: `100`, `200`, `300 Myr`
- views: `0`, `45`, `90 deg`
- outputs: sparse `dbl` products at analysis snapshots plus restart/checkpoint
  support

## Asset Gate

Current local and Nectar mirrors do not yet expose confirmed Stewart cluster
and group science environment assets.

Visible files are limited to:

- a tabulated candidate/example under
  `/Users/bwbrook/git/utas-agn/jet-setup/resources/tabulated-environments/`
- a tabulated test copy under
  `/Users/bwbrook/git/utas-agn/jet-setup/test/environment/tabulated/`
- the incomplete external `spherical-r200-n3.dbl` test fixture, with the
  corresponding `spherical-r200-n3.grid.out` still missing

The `spherical-r200-n3` test fixture must not be treated as the science
environment unless Stas/Patrick explicitly confirm it.

The GRAiLE or predecessor-project X-ray pipeline is also still a named input
gate. Do not substitute an invented X-ray path.

## Config Renderer

`scripts/science/render_three_case_configs.py` generates dry-run case bundles
containing:

- `pluto.ini`
- `environment.ini`
- `case_manifest.json`
- `definitions_overrides.json`

Example syntax-only generation:

```bash
python3 scripts/science/render_three_case_configs.py \
  --variant both \
  --grid micro \
  --output build/science/three_case_configs \
  --force
```

When the real Stewart assets are known, pass the confirmed cluster/group paths
and `--require-assets`.

`scripts/science/inspect_tabulated_environment.py` provides the lightweight
asset-inspection pass for six-column cgs tabulated environment files. Use it
before the Nectar stability gate to record rows, column ranges, radius
monotonicity, and unit assumptions for any confirmed Stewart table.

## `kunanyi` Template

`scripts/kunanyi/jet_setup_production_template.pbs` implements the validated
production shape:

- `select=N:ncpus=28:mpiprocs=28`
- `NRANKS` from `PBS_NODEFILE`
- `#PBS -M barry.brook@utas.edu.au`
- `#PBS -m ae`
- source revision logging
- case manifest logging
- generated definition overrides
- `pluto.ini` and `environment.ini` staging
- fresh/restart detection
- `DONE` and `FAILED` markers
- output-volume and artifact manifest logging

It has not yet been submitted as a live science run. The first use should be
an intermediate `C-HI` rehearsal after the Nectar gates are green.

## Next Action

1. Ask Stas/Patrick for the exact Stewart cluster and group environment files
   and the GRAiLE/predecessor X-ray pipeline assets.
2. Resize `nectar-vm` to `c3.3xlarge`.
3. Run no-jet stability checks for the confirmed Stewart environments.
4. Run the `C-HI` no-particle rehearsal to `300 Myr`.
5. Repeat `C-HI` with particles.
6. Only then use the `kunanyi` template for an intermediate rehearsal.
