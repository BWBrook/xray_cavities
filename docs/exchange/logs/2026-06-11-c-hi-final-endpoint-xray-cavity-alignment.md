# C-HI Final Endpoint X-ray/Cavity Alignment

Date: 2026-06-11

## Summary

Goal 005 produced the first final 50 Myr `C-HI`, `0 deg` X-ray/cavity
alignment gate. The final XRAiSE/GRAiLE grid X-ray path and existing
ellipsoid/ambient-shell cavity protocol both ran on the completed endpoint,
and the local alignment package reports `gate_status = green`.

## Remote Products

Input:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Output root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment
```

Stage and archive:

```text
/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment
/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/final_endpoint_xray_cavity_alignment_2026-06-11.tar.gz
sha256=2d75e982a389ac0db6f9459c14d27ab3c5e749d045da18050f47df544f4c155e
```

PBS job `697898.kunanyi-ohpc` completed extraction but exited `1` after
writing products because the wrapper's post-cavity validation used the wrong
interpreter after the HDF5 module load. The wrapper was patched to reload
`Anaconda3/2024.02-1`; a lightweight finalizer then validated the existing
outputs and wrote the archive.

## Local Assets

```text
docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/
docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md
```

The local subset includes corrected X-ray and tracer maps, cavity summary and
boundaries, scalar alignment tables, metadata, remote logs, and a review
figure. The full raw X-ray and correction-ratio TSV diagnostics remain in the
remote archive.

## Headline Metrics

- X-ray corrected 1 keV max:
  `2.874403714611562e6 mJy sr^-1`
- X-ray corrected 1 keV sum:
  `3.212610085481297e9 mJy sr^-1 pixels`
- Cavity tracer volume / accepted Level 2 volume:
  - negative z: `1.0000000000032894`
  - positive z: `1.0000000000021847`
  - bipolar total: `1.0000000000056688`
- Bipolar cavity `4pV`:
  `2.751221575650812e60 erg`
- Bipolar `4pV / Level 2 tracer-lobe energy`:
  `1.9819430042244381`
- Bipolar `4pV / Level 1 injected energy`:
  `0.8718095088507404`
- Goal 003 volume-coupled radio comparator:
  `1.6548347158067362e29 W Hz^-1`

## Recommendation

Treat the final `C-HI` endpoint X-ray/cavity path as green for review, but do
not broaden to `C-LO`, `G-LO`, multi-angle/source-age sampling, or publication
observable claims until Barry/Stas/Patrick review the cavity protocol and
decide whether a Level 3 ambient-energy/method goal is required next.
