# Handover Note: 2026-05-09 C-HI two-node restart rehearsal

The first two-node production-template restart rehearsal for the
particles-enabled `C-HI` run completed successfully on `kunanyi`.

Final successful run:

```text
PBS Job Id: 690484.kunanyi-ohpc
Job Name:   c_hi_2node_env
Exit_status=0
resources_used.cpupercent=2811
resources_used.cput=45:43:18
resources_used.mem=18587788kb
resources_used.ncpus=56
resources_used.vmem=27291908kb
resources_used.walltime=01:45:08
```

Template/runtime details:

```text
resources: select=2:ncpus=28:mpiprocs=28
exec_host: n038/0*28+n083/0*28
RUN_KIND=h5_restart_2
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 1.5 -h5restart 2
MPI_HOSTFILE=/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/job_logs/openmpi_hostfile.690484.kunanyi-ohpc.txt
```

The generated OpenMPI hostfile contained:

```text
n038.kunanyi slots=28
n083.kunanyi slots=28
```

Two useful failed attempts came first:

- `690481.kunanyi-ohpc`: OpenMPI did not infer `56` slots from PBS.
- `690483.kunanyi-ohpc`: remote node did not inherit the HDF5 runtime library
  path and failed on `libhdf5.so.310`.

The production template now:

- writes an explicit OpenMPI hostfile from `PBS_NODEFILE`
- passes the hostfile to `mpirun`
- exports `PATH`, `LD_LIBRARY_PATH`, and HDF5-related variables through
  OpenMPI

Outputs after the successful run:

```text
dbl.h5:
0 0.0000 Myr step 0
1 0.4474 Myr step 583
2 1.0102 Myr step 1146
3 2.1501 Myr step 2267

flt.h5:
0 0.0000 Myr step 0
1 0.4474 Myr step 583
2 0.9990 Myr step 1135
3 1.0102 Myr step 1146
4 1.9996 Myr step 2120
5 2.1501 Myr step 2267
```

The output directory footprint after the run was about `40 GB`, and particle
files extended through `particles.0218.dbl`.

A one-core quick-look extraction job inspected the nominal 2 Myr float output:

```text
quick-look job: 690559.kunanyi-ohpc
input: data.0004.flt.h5
timestep: Timestep_4
time: 1.9996 Myr
Exit_status=0
```

At `tracer > 5e-3`, the 2 Myr tracer extent was approximately
`x,y = +/-5.63 kpc` and `z = +/-16.5 kpc`.

Local products:

- `docs/science/c_hi_2node_quicklook_2026-05-09.md`
- `docs/science/c_hi_2node_quicklook_2026-05-09.pdf`
- `docs/science/assets/c_hi_2node_quicklook_2026-05-09/`

Compact evidence bundle:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_2node_690484_quicklook_690559_compact_2026-05-09.tar.gz
```

SHA-256:

```text
e002e0df31f5f2749ce823f7ca5b897c4b6b4cb7b322be9e29e9fb8cf9b045bb
```

Next recommended rung: a longer restart continuation aimed at the first `3-5`
regular science snapshots, still before any full 48-hour production push.
