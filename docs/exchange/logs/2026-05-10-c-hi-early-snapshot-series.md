# 2026-05-10 C-HI Early Snapshot Series

## Summary

The aligned `C-HI` smoke lane has been extended from the single 5 Myr target to
the five regular early science outputs at about `1`, `2`, `3`, `4`, and
`5 Myr`.

## Kunanyi Job

- job id: `690646.kunanyi-ohpc`
- job name: `c_hi_eseries`
- node: `n001`
- compact archive:
  `/u/bwbrook/codex_kunanyi/c_hi_early_snapshot_series_2026-05-10.tar.gz`
- SHA256:
  `503da7d4d2e80f1a2a76e5946aee59724ffe5055a71893119ef6786a06d8b68e`

The job ran truth, cavity, XRAiSE grid, and particle-radio scalar extractions
for grid outputs `2`, `4`, `6`, `7`, and `8`. Radio used the per-snapshot
Level 2 tracer side volumes.

## Products

- report:
  `docs/science/c_hi_early_snapshot_series_2026-05-10.md`
- PDF:
  `docs/science/c_hi_early_snapshot_series_2026-05-10.pdf`
- assets:
  `docs/science/assets/c_hi_early_snapshot_series_2026-05-10/`
- reusable PBS:
  `scripts/kunanyi/c_hi_early_snapshot_series.pbs`
- reusable local builder:
  `scripts/science/build_early_snapshot_series.py`

## Result

The early scalar series is coherent:

- tracer volume grows from `539.62` to `10791.77 kpc^3`
- tracer z extent grows from `10.08` to `33.04 kpc`
- by 5 Myr, Level 2 tracer-lobe energy is about `0.585` of elapsed bipolar
  injected energy
- by 5 Myr, bipolar `4pV` is about `0.804` of elapsed bipolar injected energy
- radio lobe balance stays near unity, ranging from `0.9720` to `1.0579`

## Next Move

The compact early diagnostics do not show an obvious reason to halt the setup.
The next compute-facing move should be a guarded continuation of `C-HI` toward
the first `50 Myr` milestone, probably in another bounded restart segment that
targets the next block of regular snapshots rather than a blind long push.
