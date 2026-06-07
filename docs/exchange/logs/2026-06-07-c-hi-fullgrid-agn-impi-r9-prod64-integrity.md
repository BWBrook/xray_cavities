# C-HI full-grid AGN/IMPI 64-node production endpoint integrity

Date: 2026-06-07

## Summary

The completed 64-node production endpoint from `697298.kunanyi-ohpc` passed a
focused product-integrity/readability check under the AGN Intel/IMPI HDF5
stack.

The endpoint remains:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles
```

## Stack

The check loaded the same AGN family used for production:

```text
intel/18.0.1.163
impi/2018.1.163
hdf5/1.12.1p
zfp/0.5.5
```

Resolved HDF5 tools:

```text
h5ls=/ds/projects/agn/libraries/hdf5p/1.12.1-impi/bin/h5ls
h5dump=/ds/projects/agn/libraries/hdf5p/1.12.1-impi/bin/h5dump
```

## Catalogue Tails

Final double-output catalogue:

```text
dbl.h5.out lines=12
6 9.198040e+03 3.139112e-01 29722 single_file little rho vx1 vx2 vx3 prs tr1
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
10 1.379684e+04 3.139112e-01 44372 single_file little rho vx1 vx2 vx3 prs tr1
11 1.533007e+04 1.377728e-01 49253 single_file little rho vx1 vx2 vx3 prs tr1
```

Final float-output catalogue:

```text
flt.h5.out lines=52
46 1.379684e+04 3.139112e-01 44372 single_file little rho vx1 vx2 vx3 prs tr1
47 1.410353e+04 3.139112e-01 45349 single_file little rho vx1 vx2 vx3 prs tr1
48 1.441022e+04 3.139112e-01 46326 single_file little rho vx1 vx2 vx3 prs tr1
49 1.471660e+04 3.139112e-01 47302 single_file little rho vx1 vx2 vx3 prs tr1
50 1.502329e+04 3.139112e-01 48279 single_file little rho vx1 vx2 vx3 prs tr1
51 1.533007e+04 1.377728e-01 49253 single_file little rho vx1 vx2 vx3 prs tr1
```

## Product Counts And Sizes

Regular files produced inside the isolated production continuation workdir:

```text
dbl_h5_count=2
flt_h5_count=8
particle_count=723
final_particle=particles.5000.dbl
restart_out_size=1536
```

These counts intentionally exclude symlinked restart inputs inherited from the
clean fresh run.

Final file sizes and file signatures:

```text
data.0011.dbl.h5 size=67318639276 type=Hierarchical Data Format (version 5) data
data.0011.dbl.xmf size=3011 type=XML 1.0 document, ASCII text
data.0051.flt.h5 size=44890581676 type=Hierarchical Data Format (version 5) data
data.0051.flt.xmf size=3011 type=XML 1.0 document, ASCII text
particles.5000.dbl size=23608389 type=data
restart.out size=1536 type=data
```

## HDF5 Structure

`data.0011.dbl.h5` contains the expected final double-output datasets:

```text
/Timestep_11/vars/prs Dataset {1014, 960, 960}
/Timestep_11/vars/rho Dataset {1014, 960, 960}
/Timestep_11/vars/tr1 Dataset {1014, 960, 960}
/Timestep_11/vars/vx1 Dataset {1014, 960, 960}
/Timestep_11/vars/vx2 Dataset {1014, 960, 960}
/Timestep_11/vars/vx3 Dataset {1014, 960, 960}
```

`data.0051.flt.h5` contains the expected final float-output datasets:

```text
/Timestep_51/vars/prs Dataset {1014, 960, 960}
/Timestep_51/vars/rho Dataset {1014, 960, 960}
/Timestep_51/vars/tr1 Dataset {1014, 960, 960}
/Timestep_51/vars/vx1 Dataset {1014, 960, 960}
/Timestep_51/vars/vx2 Dataset {1014, 960, 960}
/Timestep_51/vars/vx3 Dataset {1014, 960, 960}
```

Scalar reads from the final double and float files succeeded:

```text
data.0011.dbl.h5 /Timestep_11/vars/rho 0.00107249
data.0011.dbl.h5 /Timestep_11/vars/vx1 4.80256e-05
data.0011.dbl.h5 /Timestep_11/vars/tr1 0
data.0051.flt.h5 /Timestep_51/vars/rho 0.00107249
data.0051.flt.h5 /Timestep_51/vars/vx1 4.80256e-05
data.0051.flt.h5 /Timestep_51/vars/tr1 0
```

Both final XMF sidecars reference `<Time Value="1.533007e+04"/>` and point to
the matching final HDF5 files/datasets.

## Particle File Header

The final particle file header is consistent with the final PLUTO step and
catalogue time:

```text
# PLUTO 4.4-patch3 (Sep 2024) binary particle data file
# dimensions     3
# nflux          5
# dt_particles   1.010101e+38
# endianity      little
# nparticles     196732
# idCounter      196732
# particletype   1
# precision      double
# time           1.533006968940e+04
# stepNumber     49253
# nfields        13
# nelem          15
# field_names    id  x1  x2  x3  vx1  vx2  vx3  tinj  color  tracer  last_shock_time  density  pressure
```

## Interpretation

The final `dbl`, `flt`, XMF, particle, and catalogue products are present and
readable. This supports treating the 64-node `prod64` tree as the completed
science production endpoint before moving to compact quick-look extraction and
downstream analysis.
