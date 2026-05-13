# 2026-05-13 C-HI Run Configuration Audit

## Context

After Barry's third meeting with Stas and Patrick, the next immediate request
was to expose the concrete `C-HI` run configuration before moving toward a
full-grid production launch. Patrick asked for run size, output file sizes,
modules/library versions, and explicit run parameters in reports. Stas asked
to inspect the actual grid and resolution choices in `pluto.ini`.

## Actions

- Fetched live `kunanyi` configuration inputs from the completed
  `691422.kunanyi-ohpc` run:
  - `pluto.ini`
  - `environment.ini`
  - `case_manifest.json`
  - `definitions_overrides.json`
  - `definitions_usr.h`
  - generated `grid.out`
  - `flt.h5.out`, `dbl.h5.out`, `restart.out`
  - output file size catalogue
  - PBS/module metadata
- Added `scripts/science/build_c_hi_run_config_audit.py` to produce:
  - `run_config_summary.json`
  - `grid_resolution_summary.csv`
  - `output_file_size_summary.csv`
  - `flt_output_times.csv`
  - `dbl_output_times.csv`
  - `c_hi_reduced_grid_cell_widths.png`
- Added the report:
  - `docs/science/c_hi_run_configuration_audit_2026-05-13.md`
  - `docs/science/c_hi_run_configuration_audit_2026-05-13.pdf`
- Updated the 8-node mini-production report with a concrete run-spec block:
  - `docs/science/c_hi_8node_mini_production_2026-05-13.md`
  - `docs/science/c_hi_8node_mini_production_2026-05-13.pdf`
- Updated the production PBS template so future runs record git root, branch,
  head SHA, status, missing-git state, and PLUTO binary SHA-256.
- Updated the through-33-Myr particle-HDF5 wrapper to request `48gb` memory on
  future reruns. The completed scheduler-fit run used the temporary `16gb`
  request but reported roughly `43 GB` memory use, so future declarations
  should be more honest even if they queue longer.
- Opened an agent-communications review thread:
  - `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md`

## Key Findings

- The completed `691422.kunanyi-ohpc` run is a healthy 8-node reduced-grid
  mini-production segment:
  - `224` MPI ranks
  - final time `33.374180 Myr`
  - final restart-capable checkpoint `data.0012.dbl.h5`
  - output footprint about `217G`
- The run used the reduced `kunanyi_single_node_250` grid:
  - generated grid: `404 x 404 x 452`
  - X1/X2: `+/-200 kpc`
  - X3: `+/-250 kpc`
  - central cell width: `0.05 kpc`
  - cell width near `200 kpc`: about `11.08 kpc` in X1/X2 and `8.39 kpc` in X3
- This grid is suitable for the reduced-grid rehearsal lane, but it is not the
  final full-grid production configuration.
- The intended production-grid review target remains `stewart_stretched_250`
  from `scripts/science/render_three_case_configs.py`.

## Diagnostic Status

The through-33-Myr diagnostic chain is partly complete:

- `691762.kunanyi-ohpc` (`c_hi_ph5_33`) completed and rebuilt the particle HDF5
  cache through the new particle outputs.
- `691763.kunanyi-ohpc` (`c_hi_s33`) was running at the last poll
  (`2026-05-13 14:52 AEST`) and should be harvested after the PBS email lands.

## Next

1. Harvest `691763.kunanyi-ohpc` when complete and build the through-33-Myr
   scalar diagnostic report.
2. Ask Patrick's and Stas' agents to review the new configuration audit and
   confirm whether the final `stewart_stretched_250` production render needs
   changes.
3. Only after that review, launch a bounded full-grid production startup or
   48-hour segment.
