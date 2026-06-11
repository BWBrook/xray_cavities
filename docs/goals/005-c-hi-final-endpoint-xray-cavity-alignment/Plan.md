# Plan: Goal 005 C-HI Final Endpoint X-ray/Cavity Alignment Gate

## Intended Shape

Produce a final-endpoint alignment gate, not a broad production step.

```text
50 Myr C-HI final endpoint
  + 0 deg XRAiSE/GRAiLE grid X-ray
  + ellipsoid/ambient-shell cavity protocol
  + accepted Level 1/2 truth
  + Goal 003 radio-volume scalars
  -> compact X-ray/cavity/truth/radio alignment package
  -> reviewed next-gate recommendation
```

The result should tell Barry, Stas, and Patrick whether the first full `C-HI`
run can support a coherent final endpoint X-ray/cavity measurement path before
the project spends effort on `C-LO`, `G-LO`, viewing-angle sampling, or new
production runs.

## Likely Files

Likely creates or modifies:

- `scripts/science/build_final_xray_cavity_alignment.py`
- `tests/test_final_xray_cavity_alignment.py`
- `scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`
- `docs/exchange/logs/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment.md`
- `docs/exchange/current_status.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`

It may instead adapt existing final/smoke helpers if that is cleaner, but the
diff should keep final endpoint products clearly separated from historical
5 Myr smoke products.

## Work Plan

1. Record starting state in `Log.md`.
2. Read the Goal 005 packet, repo contract, accepted Goal 004 audit, and the
   5 Myr XRAiSE/cavity smoke notes.
3. Inspect the existing XRAiSE/cavity scripts and PBS wrappers.
4. Decide whether to create a combined final wrapper or separate final X-ray
   and cavity wrappers. Prefer the smallest path that leaves provenance clear.
5. Add focused tests for any local parser, summary merger, metadata checker,
   or alignment-table builder before relying on it.
6. Implement or adapt final-specific local helpers.
7. Run local tests and PBS syntax checks before remote submission.
8. Perform a read-only remote preflight for the final HDF5, timestep,
   correction tables, staged scripts, and runtime modules.
9. Run bounded final endpoint X-ray/cavity post-processing on `kunanyi`.
10. Pull or unpack only compact review artefacts into `docs/science/assets/`.
11. Build the alignment package against accepted final truth/radio artefacts.
12. Write the science note, exchange log, and current-status update.
13. Run final validation gates.
14. Wake X-ray Cavities with the complete review packet.

## Expected Judgement Calls

Be conservative about scientific interpretation:

- A finite final X-ray map proves the final grid X-ray path, not the full
  observational treatment.
- Finite cavity `pV` and `4pV` prove that the current cavity geometry/ambient
  shell can be applied at 50 Myr, not that the protocol is the final physical
  word.
- Sound, buoyancy, and refill ages should be labelled according to the actual
  assumptions used by the extractor.
- Level 3 ambient energy remains outside this goal unless the work reveals a
  narrow input needed for later method design.
- Goal 003 radio scalars are continuity comparators, not a replacement for a
  beam/instrument-aware radio observable.

Expected successful comparison rows:

- final X-ray map max/sum and finite-pixel counts;
- final cavity `pV`, `4pV`, and age estimates by lobe and bipolar total;
- Level 1 injected energy by side and bipolar total;
- Level 2 tracer-lobe volume/energy by side and bipolar total;
- Goal 003 volume-coupled radio scalar by side and bipolar total where
  available;
- ratios such as `4pV / injected_energy` and `4pV / tracer_lobe_energy`, with
  units and caveats explicit.

## Non-Goals

Do not open a new production case. Do not make the first pass multi-angle.
Do not add detector response or beam convolution. Do not solve Level 3 ambient
energy inside this goal. Do not hide failed assumptions behind a polished
figure. A sharp blocker is better than a misleading green product.
