# 2026-05-13 - C-HI 8-Node Mini-Production Complete

## Result

The scheduler-fit `C-HI` mini-production continuation completed cleanly:

```text
PBS Job Id: 691422.kunanyi-ohpc
Job Name:   c_hi_8mini
Exit_status=0
resources_used.ncpus=224
resources_used.walltime=14:45:00
```

The run used:

```text
select=8:ncpus=28:mpiprocs=28
NRANKS=224
RUN_KIND=h5_restart_7
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 14.5 -h5restart 7
```

## Output State

The run restarted from `data.0007.dbl.h5` at `10.278362 Myr` and advanced to
`33.374180 Myr`.

Important outputs now include:

- regular `flt.h5` outputs through `data.0039.flt.h5`
- restart-capable `dbl.h5` outputs through `data.0012.dbl.h5`
- particle files through `particles.3343.dbl`
- output volume: `217G`

Selected times:

| Output | Time (`Myr`) | Type |
| ---: | ---: | --- |
| `15` | `10.2784` | `flt.h5` |
| `20` | `14.9993` | `flt.h5` and `dbl.h5` checkpoint `8` |
| `25` | `19.9997` | `flt.h5` and `dbl.h5` checkpoint `9` |
| `30` | `24.9992` | `flt.h5` and `dbl.h5` checkpoint `10` |
| `35` | `29.9996` | `flt.h5` and `dbl.h5` checkpoint `11` |
| `39` | `33.3742` | final `flt.h5` and `dbl.h5` checkpoint `12` |

## Local Artifacts

Compact run metadata was fetched to:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_8mini_691422_compact_2026-05-13.tar.gz
```

The meeting-facing report and PDF are:

```text
docs/science/c_hi_8node_mini_production_2026-05-13.md
docs/science/c_hi_8node_mini_production_2026-05-13.pdf
```

## Follow-Up Diagnostics

Two dependent jobs have been submitted:

```text
691762.kunanyi-ohpc  c_hi_ph5_33
691763.kunanyi-ohpc  c_hi_s33
```

The first rebuilds the particle HDF5 through the new particle outputs. The
second extracts the compact scalar series for outputs:

```text
15 20 25 30 35 39
```

When the diagnostic emails land, fetch the archives:

```text
/u/bwbrook/codex_kunanyi/c_hi_to33_particle_hdf5_2026-05-13.tar.gz
/u/bwbrook/codex_kunanyi/c_hi_to33_snapshot_series_2026-05-13.tar.gz
```

Then build the extended through-33-Myr scalar report.
