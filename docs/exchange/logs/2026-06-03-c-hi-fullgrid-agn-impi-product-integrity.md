# 2026-06-03 C-HI Full-Grid AGN IMPI Product Integrity Check

## Summary

The final products from fresh 80-node job `696619.kunanyi-ohpc` were checked
in place on Kunanyi. The final double and float HDF5 outputs are readable, the
XMF sidecars reference the expected final time, `restart.out` is present, and
the final particle file header matches the final catalogue time and step.

No large files were copied off Kunanyi.

## Target Run

- Run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles`
- Output directory:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs`
- Module stack used for the check:
  `intel/18.0.1.163`, `impi/2018.1.163`, `hdf5/1.12.1p`, `zfp/0.5.5`
- HDF5 tools:
  `/ds/projects/agn/libraries/hdf5p/1.12.1-impi/bin/h5ls` and
  `/ds/projects/agn/libraries/hdf5p/1.12.1-impi/bin/h5dump`

## Catalogue Consistency

`dbl.h5.out` has 10 entries and ends at output `9`:

```text
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

`flt.h5.out` has 44 entries and ends at output `43`:

```text
41 1.257039e+04 3.139112e-01 40465 single_file little rho vx1 vx2 vx3 prs tr1
42 1.287708e+04 3.139112e-01 41442 single_file little rho vx1 vx2 vx3 prs tr1
43 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

Counts:

```text
dbl_h5_count=10
flt_h5_count=44
particle_count=4278
final_particle=particles.4277.dbl
```

## Final File Stats

```text
data.0009.dbl.h5  size=67318639276  HDF5
data.0009.dbl.xmf size=3005         XML
data.0043.flt.h5  size=44890581676  HDF5
data.0043.flt.xmf size=3011         XML
particles.4277.dbl size=20220069    binary particle data
restart.out        size=1280        binary restart data
```

## HDF5 Structure

`data.0009.dbl.h5`:

```text
/Timestep_9/vars/prs Dataset {1014, 960, 960}
/Timestep_9/vars/rho Dataset {1014, 960, 960}
/Timestep_9/vars/tr1 Dataset {1014, 960, 960}
/Timestep_9/vars/vx1 Dataset {1014, 960, 960}
/Timestep_9/vars/vx2 Dataset {1014, 960, 960}
/Timestep_9/vars/vx3 Dataset {1014, 960, 960}
```

`data.0043.flt.h5`:

```text
/Timestep_43/vars/prs Dataset {1014, 960, 960}
/Timestep_43/vars/rho Dataset {1014, 960, 960}
/Timestep_43/vars/tr1 Dataset {1014, 960, 960}
/Timestep_43/vars/vx1 Dataset {1014, 960, 960}
/Timestep_43/vars/vx2 Dataset {1014, 960, 960}
/Timestep_43/vars/vx3 Dataset {1014, 960, 960}
```

Scalar data reads succeeded:

```text
data.0009.dbl.h5 /Timestep_9/vars/rho  (0,0,0): 0.00106042
data.0009.dbl.h5 /Timestep_9/vars/vx1  (0,0,0): 4.16167e-05
data.0043.flt.h5 /Timestep_43/vars/rho (0,0,0): 0.00106042
data.0043.flt.h5 /Timestep_43/vars/vx1 (0,0,0): 4.16167e-05
```

## XMF and Particle Readability

Both XMF sidecars reference time `1.311314e+04` and the expected final HDF5
files. The final particle file header reports:

```text
# PLUTO 4.4-patch3 (Sep 2024) binary particle data file
# dimensions     3
# nflux          5
# endianity      little
# nparticles     168496
# idCounter      168496
# particletype   1
# precision      double
# time           1.311314069772e+04
# stepNumber     42194
# nfields        13
# nelem          15
# field_names    id  x1  x2  x3  vx1  vx2  vx3  tinj  color  tracer  last_shock_time  density  pressure
```

## Restart Readiness

The final double HDF5 output, XMF sidecar, final particle file, and
`restart.out` are all present and readable. This is enough evidence to proceed
to a short bounded 80-node restart probe from output `9` under the same AGN
Intel/IMPI stack with `HDF5_USE_FILE_LOCKING=FALSE`.
