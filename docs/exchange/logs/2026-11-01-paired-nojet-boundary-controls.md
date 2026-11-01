# Paired coarse boundary controls — 1 November 2026

Barry: “Go ahead with the cheap paired reflective/outflow controls, keeping
everything else identical. Hold off on a full production-matched run.” This is
a continuation of turn #5; no return to Claude yet.

Implemented a staged-only PLUTO/jet-setup patch, one common binary workflow,
four fresh 400 × 400 × 500 controls, exact numerical boundary-flux and source
accounting, and independent native/budget validators. Original checkouts and
production inputs are untouched. The scientific plan and local evidence are
in `docs/science/paired_nojet_boundary_experiment_2026-11-01.md`.

Initial local verification: 76 tests pass with one expected exported-stage-only
skip; all 77 pass in the exported stage. Full serial compile/link passes.
Independent review required and obtained true gross conversion-energy changes
and zero-failure gates before interpreting repair magnitude. Remote MPI/HDF5
build, four full-grid smokes, paired identity and closure remain required.
