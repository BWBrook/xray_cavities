# 2026-07-12 - G-LO Endpoint First Products And Three-Case Comparison

Status: `complete_product`.

Decision label:
`THREE_CASE_ENDPOINT_FIRST_PRODUCTS_COMPLETE`.

Goal 039 submitted job `756090.kunanyi-ohpc` / `g_lo_xprod` after local tests,
remote staged-hash checks, endpoint HDF5 validation, reference-table checks,
runtime-input checks, and remote wrapper syntax all passed.

The job generates G-LO endpoint `0/45/90 deg` X-ray/tracer products and a
nine-row `C-HI`/`C-LO`/`G-LO` endpoint comparison. It performs no new
simulation or radio/cavity workflow.

The job completed with `Exit_status=0` after `00:29:05`. The retrieved archive
hash is `149141739f6f8a631b94425230d5e824f6efc426c0ddc25dacd84aacb73e4e99`;
stderr is empty and all archive checksums pass.

All nine products have zero empty columns. C-LO corrected sums remain
approximately 0.97-1.09 of C-HI, while G-LO is approximately 0.047-0.062 of
C-HI. This is a robust processed-total contrast, not yet a cavity or feedback
interpretation.

Next: three-case endpoint cavity-recovery and Level 1/2 truth alignment using
existing outputs. No new production run is indicated.
