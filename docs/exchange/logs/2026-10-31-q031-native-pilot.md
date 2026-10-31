# Q-031 C-HI/G-HI native pilot

Barry authorised the fixed C-HI and G-HI 40 Myr pilot, including clamp
sensitivity, on 31 October 2026. This is post-processing of retained simulation
outputs. The accepted method is in
`docs/science/q031_native_path_length_design_2026-10-31.md`.

## Implementation and review

`build_q031_native_emission.py` reuses the exact Q-029 factor-1 shock-mask
helpers and strict float64 `tr1 > 1e-3` cocoon mask. Both cases require
quantitative bilateral shocks. It computes current and case-specific initial
emission through the current masks, at 0/45/90 degrees, using both retained
linear extrapolation and independently clamped table coordinates. Signed
contributions, table-domain coverage and pre-sanitization failures remain
visible. These are diagnostic products; numerical validation does not establish
the physical adequacy of either extrapolation convention.

Independent science review led to explicit regional volume/mass/emission
closures, Q-029 mass anchors, saved density/temperature distributions, separate
raw-kernel and corrected-emissivity failure diagnostics, and geometry refinement
checks. Independent launch review led to source binding against the validated
flux inputs, imported-library identity checks, mandatory real-kernel smoke
evidence, and transactional package verification.

Final science review also made the reference age/source/calibration fields
mandatory. It independently checked the asymmetric 90-degree projection against
the sign-reversed direct x-sum and chunked projections against one-pass
projections (maximum discrepancy `4.44e-16`). The final local six-file
deployment suite passed all 79 tests, including the real-kernel subprocess CLI.
Both frozen C-HI/G-HI reference bundles pass the strengthened binding checks.

The launch wrapper checks the completed ten-unit migration and its links,
rejects unresolved migration tombstones, and verifies the flux package before
any native reads. The selected native paths and metadata must match the flux
provenance. Device identifiers are recorded but not compared across allocations
because NFS device numbers can differ between nodes; the native process checks
them before and after its own read. Literal source paths and resolved paths are
both preserved.

The result package contains the six science outputs and manifest for each
case, dependency records before and after extraction, source/runtime checksums,
smoke evidence and per-case resource records. Native payloads and temporary
mask caches remain on Kunanyi.

## Resource and dependency plan

The target smoke uses 2 CPUs, 8 GB and a one-hour limit. The pilot uses 2 CPUs,
128 GB and a 24-hour limit, processing cases sequentially. Historical Q-029
mask extraction peaked near 41 GB; native inputs already reside on Kunanyi.
The pilot is submitted only after the target smoke passes, with explicit PBS
`afterok` dependencies on that smoke, migration `870323.kunanyi-ohpc` and flux
`870374.kunanyi-ohpc`. Receipt checks remain mandatory even after PBS releases
the dependency hold.

At 11:32 UTC, migration was running (7:42:51 elapsed) and flux was held behind
recovery/migration. Native scientific results are pending.
