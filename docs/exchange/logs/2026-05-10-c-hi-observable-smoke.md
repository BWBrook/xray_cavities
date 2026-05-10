# 2026-05-10 - C-HI 5 Myr Observable Smoke

## Summary

The first aligned observable smoke product now exists for the same `C-HI`
snapshot used by the truth smoke:

- grid file:
  `/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem/outputs/data.0008.flt.h5`
- timestep: `Timestep_8`
- grid time: `4.9994348189788402 Myr`
- particle file:
  `/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem/outputs/particles.0503.dbl`
- particle time: `4.9994348189790641 Myr`
- view: `0 deg`

Job `690612.kunanyi-ohpc` completed the extraction on node `n001` and wrote a
compact archive.

## Important Caveat

This is a bridge observable smoke, not the final GRAiLE/XRAiSE science
pipeline. The supplied GRAiLE/XRAiSE assets are present locally, including the
APEC table and Gaunt lookup table, but the baseline `kunanyi` environment does
not provide the needed Python analysis packages (`numpy`, `h5py`, `scipy`,
`astropy`, `numba`, `matplotlib`, `yaml`, `hdf5plugin`). The smoke extractor
therefore runs as a small C/HDF5 compute-node program and ports:

- the XRAiSE grid bremsstrahlung expression before APEC/Gaunt correction
- the lossless `plutokore` pressure/tracer radio surface-brightness scaling
- a PLUTO particle-file reader for aligned particle positions

## Artifacts

Report:

- `docs/science/c_hi_observable_smoke_2026-05-10.md`
- `docs/science/c_hi_observable_smoke_2026-05-10.pdf`

Figure and compact products:

- `docs/science/assets/c_hi_observable_smoke_2026-05-10/`

Local compact archive:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_observable_smoke_690612_compact_2026-05-10.tar.gz
```

SHA-256:

```text
477b576e9eacb662b9ed715e3737eecbe44f7b0121f66bcc19d9adc7ec78805e
```

New workflow helpers:

- `scripts/science/pluto_h5_observable_smoke_extract.c`
- `scripts/science/plot_observable_smoke.py`
- `scripts/kunanyi/c_hi_observable_smoke.pbs`
- `scripts/kunanyi/copy_to_kunanyi.sh`
- `scripts/kunanyi/fetch_from_kunanyi.sh`

## Metrics

- particles loaded: `16056`
- particle extent: about `+/-8.9 kpc` in `x/y`, `+/-32.2 kpc` in `z`
- raw 1 keV X-ray map max: `1.4382e6 mJy sr^-1`
- 150 MHz radio proxy max: `6.6204e15 mJy sr^-1`
- 150 MHz radio luminosity proxy: `5.4149e26 W Hz^-1`
- lobe/tracer cells included at `tracer > 5e-3`: `14296426`

## Next Recommended Step

The truth plus bridge-observable smoke package is now green for the `5 Myr`,
`0 deg` target. Next, either:

1. set up the proper Python GRAiLE/XRAiSE analysis runtime and rerun this same
   target with the full loss-kernel pipeline, or
2. add the first cavity-protocol stub for this target while the Python runtime
   is being sorted out.
