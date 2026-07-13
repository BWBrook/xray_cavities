# 2026-07-12 - Three-case endpoint cavity recovery and truth alignment

Status: `complete_product`.

Decision label:
`THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE`.

Goal 040 completed a common X-ray-only recovery and Level 1/2 truth-alignment
surface for C-HI, C-LO, and G-LO at `0/45/90 deg`. The accepted base mask is
the highest-deficit 1 percent of projected physical area inside 120 kpc, after
a tracer-blind radial-background correction. It returns two opposite-side
components in all nine panels. Pixel-count weighting was rejected during the
final audit because unequal projected pixel areas caused false view dependence;
the corrected method is regression-tested.

At tracer threshold `5e-3`, base X-ray precision is `1.0` and tracer recall is
`0.0208-0.0303` for C-HI, `0.1927-0.2015` for C-LO, and `0.0897-0.1099` for
G-LO. Geometric X-ray volume divided by Level 2 tracer-lobe volume is
`0.00740-0.00804`, `0.3906-0.3918`, and `0.0655-0.0656`, respectively.

PBS job `756092.kunanyi-ohpc` / `tri_truth` finished with `Exit_status=0`,
walltime `00:22:16`, empty stderr, all case validation markers, and aggregate
truth validation passed. The retrieved compact archive SHA-256 is
`474c06f81d09acdb616345bc56d7919738d894d317b0d98a1fee7f941b9d2e6b`.
`Stageout_status=1` is retained as a scheduler caveat, but requested artifacts
were present and retrieved directly.

Using side-specific tracer-shell pressure, the adopted geometric-depth
`2.5pV` hybrid proxy spans `0.00358-0.00389` of Level 1 for C-HI,
`0.478-0.480` for C-LO, and `0.0497-0.0499` for G-LO. These are explicitly
hybrid tracer-pressure/X-ray-volume proxies, not observer-only cavity energies.
No final observational topology or publication-facing claim is frozen.
