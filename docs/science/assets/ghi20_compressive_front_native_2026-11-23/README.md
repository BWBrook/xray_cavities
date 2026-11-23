# G-HI/20 native compression-layer evidence

The production source is the 960 × 960 × 1,014 stretched grid of G-HI, at 19.9996143 Myr (`Timestep_20`, code time 6131.909618), paired with its initial fields. Cell widths run from 0.05 kpc to 1.692 kpc transversely or 2.104 kpc axially. The tabulated group atmosphere is 002031. Each jet has labelled kinetic power $10^{45}$ erg s$^{-1}$ at 0.1$c$; the run uses HLLC, CFL 0.33 and approximately one Myr between single-precision fluid outputs. The retained 1-keV sky projections use redshift 0.05 and three side-on azimuths (0°, 45°, 90°). The [native contract](../../ghi20_compressive_front_contract_2026-11-23.md) was frozen at `8905180`. [Production budget and emission metadata](../../turn15_energy_emission_review_2026-11-11.md)

The native validation tested 320 planar cases (two placements, four orientations, ten physical profiles and four selector arms) before opening any alignment. All 256 required rows passed. Each known shock and positive acoustic compression had selected cells within two local widths of its centre plane. The required nulls, including pressure-balanced converging contacts, produced zero cells. The 64 sensitivity rows all detected the Mach-1.1 shock or the broader acoustic compression. The matrix records the width of each detected layer separately. A synthetic compressing sphere on the actual core axes was selected along all three directions on both sides, with identical tiled and untiled output. The positive-control radius was 1.008 kpc and the maximum selected cell-centre extent was 1.125 kpc on all three axes. [All rows](synthetic_validation.csv) · [Grid, atmosphere and validation receipt](synthetic_validation.json)

To rerun with public files, from the repository root:

```sh
.venv/bin/python scripts/science/compressive_front_native_validate.py \
  --grid docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage/completion_evidence/grid.out \
  --output /tmp/ghi20-compression-validation
.venv/bin/python -m pytest -q tests/test_compressive_front_native.py tests/test_q032_source_emission.py
```

The public grid comes from G-LO. Every physical edge on each axis equals the corresponding G-HI edge bit for bit; the header timestamp differs. The matrix reproduces identically. The `exact_grid_file_sha256` field distinguishes the files. The [historical shock-specific negative result](../../independent_bow_shock_validation_2026-11-04.md) remains part of the record.

An independent replay on the actual extraction host passed both original source checks, including the inherited G-HI production chain. Both HDF5 files retain the archived device number 46 and all other native identity fields. The primary extractor also hashes their full 44,890,581,676 bytes apiece. [Original gate replay](worker_native_identity.json) · [Replay implementation](../../../../scripts/science/compressive_front_native_identity.py)
