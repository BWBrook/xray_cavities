# Goal 045 X-ray Cavity Recovery Method Refinement

Date: 2026-07-23
Status: `complete_product`

Goal 045 follows the Goal 044 failed-closed result without changing or
overwriting that evidence. The projector is already validated. This goal
repairs the downstream recovery estimand and validation design using the
existing Goal 044 maps only.

The frozen method treats the one-percent residual core as a seed detector,
fits a robust degree-6 normalized Chebyshev log-intensity background, grows
separate negative-z and positive-z components through robust tracer-blind
support, uses area-weighted metrics, rejects unresolved geometry, and compares
direct-90 and edge-90 recovery only after both have been mapped to a third
symmetric common grid. Degree-5/6/7 stability and independent radial negative
controls are required gates.

Local synthetic validation passed all predeclared gates: 12/12 side-angle
recoveries, 18/18 negative controls, resolved geometry, minimum IoU `0.79044`,
and maximum volume-proxy error `0.286441`. The combined focused and legacy
suite passed with `69 passed`; remote hashes, syntax, Python compilation, and
source preflight passed.

PBS job `775522.kunanyi-ohpc` (`xcav_refine`) was submitted to `normal` and
verified queued at `Thu Jul 23 14:11:47 2026`. It requests one CPU, `16gb`,
and `01:00:00`. The job only evaluates existing Goal 044 maps and archives
green or failed-closed evidence. No XRAiSE or PLUTO rerun is permitted.

Completion: PBS job `775522.kunanyi-ohpc` ended with `Exit_status=0`,
walltime `00:00:30`, and empty stderr. The validator passed `7/7` gates. The
retrieved archive SHA-256 is
`462199cc4537cf987556c04961dd807e5a0a465ede40f0af46c1c2f34a4675a1`;
it opens and all internal checksums pass.

Decision:
`XRAY_CAVITY_RECOVERY_METHOD_REFINEMENT_GREEN`.

Goal 045 resolves Goal 044's recovery-method and common-grid defects for the
fixture-informed production path. The X-ray-validation lifecycle hold can be
lifted in the Goal 042 dependency ledger, but no deletion is authorized here
and publication-facing observational certification remains out of scope.

Science note:
`docs/science/xray_cavity_recovery_method_refinement_2026-07-23.md`.
