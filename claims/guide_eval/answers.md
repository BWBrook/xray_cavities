# Answer key

Each answer is valid as of the guide and ledger at the 4 November BND-02 update or later.
Update an answer when the claim it cites changes status.

1. **NAT-01.** 2.5pV/E_inj is 0.525–0.559 (C-HI), 0.468–0.498 (G-HI),
   0.615–0.785 (G-LO) and 0.631–1.108 (C-LO). α = 2.5 is primary; α = 4 is a
   literature comparator only.
   *Trap:* presenting 4pV as primary, or calling the C-LO range certified
   clean: BND-04 bounds its boundary exposure only on the coarse controls.
2. **No.** The number comes from the legacy 1% selector: OBS-01 is refuted
   and OBS-02 withdrawn. Recovery is unestablished until a detector passes
   (DET-01).
   *Trap:* quoting the number with a caveat.
3. **BND-01** is supported: every case exceeds injection, C-LO by 6–24×.
   **BND-02** is supported on coarse controls: jet-independent inflow through
   the outflow faces, growing as t², matched the prediction frozen beforehand
   to 2–7%. It accounts for about 97% of C-LO's excess. **BND-05** is open:
   5–19% of E_inj remains in C-HI, G-HI and G-LO after the boundary term is
   subtracted.
   *Trap:* calling it jet heating, or saying the boundary explains all of the
   excess in every case.
4. **NAT-05.** Full cells with tr1 > 1e-3, after promotion to double
   precision. Binary volumes are 3.8–6.1× the fractional ones at 10 Myr, and
   the C-LO X-ray/native ratio moved from 6.76 to 0.494 on this definition
   alone. Tracer-defined cocoons are not X-ray cavities (XR-02).
5. **G-HI at 50 Myr.** Its lobe reaches the z boundary: from snapshot 48 the
   axial edge pressure rises to 140–315 times its initial value, and the
   final margin is 1.05 kpc
   (`four_case_boundary_spectral_field_review_2026-08-28.md`). Score 1 for
   naming the exclusion without the boundary-contact reason.
6. **Not necessarily.** At the 5% rung, completeness is 0.36 and purity
   0.70–0.77, so the errors cancel (DET-02). Check per-side completeness and
   purity, and the four-case contrasts.
   *Trap:* accepting the detector on volume ratio alone.
7. **No.** They use reflective boundaries on a uniform 1 kpc grid; production
   uses outflow boundaries on a stretched grid (BND-03 caveat). Their
   quietness says nothing about production boundary inflow.
   *Trap:* answering yes.
8. **Barry's explicit authorisation.** No new PLUTO run is allowed without
   it. Post-processing of existing outputs is allowed.
9. **DET-01.** Detection efficiency that depends on cocoon contrast, and
   segmentation (background merges, off-axis selection, aperture clipping).
   Planned rungs: a t = 0 baseline, aperture sensitivity, a background-merge
   guard, topology validation and an emission-defined native reference
   (XR-02).
10. **DET-01 `reproduce`:**
    `uv run python scripts/science/summarise_q032_retained_ladder.py`, run on
    the retained method-ladder rows, with `--native-root` pointing at the
    Q-029 `remote_analysis` directory. Both inputs are in the repository.
11. **DET-03.** Yes. The C-HI tracer area inside the aperture is 0.92, 0.72
    and 0.57 at 30, 40 and 50 Myr. Up to 43% of the late cocoon is removed
    from any method.
12. **BND-05.** The residual excess after the boundary term is settled by the
    Q-031 production flux job, which measures face transport and nozzle
    delivery. The spherical 100/300 km/s budgets (Stas's 4 November
    priority) or XR-02, given with sound reasons, score 1.
