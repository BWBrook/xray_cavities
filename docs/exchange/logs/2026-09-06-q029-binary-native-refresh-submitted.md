# Q-029 submitted, awaiting completion notification

Barry authorised the strict binary native cocoon refresh on 2026-09-06.
Implemented full-cell `float64(tr1) > 0.001` and complementary ambient masks,
initial-nozzle-aware energy allocations, stable regional energy changes,
precision diagnostics and a combined native/shock read pass. Fractional and
alternative binary masks remain sensitivities. The observer measurements,
accepted axial fronts and no-jet calibrations are reused.

The preliminary native/X-ray join preserves 37 valid and 20 censored views.
Pressure recovery is within a factor of two for 36/37 usable views, volume for
4/37 and enthalpy for 5/37. C-LO's median enthalpy recovery ratio changes from
6.76 to 0.494. These are preliminary until production acceptance and threshold
precision review. The frozen design, requested 10 Myr values, provenance and
resume instructions are in
`docs/science/q029_binary_native_refresh_2026-09-06.md`.

Validation: 74 focused tests passed, plus shell syntax and diff checks. Remote
preflight verified 31 staged files, upload checksum and Python imports. PBS
`790871.kunanyi-ohpc` was submitted once and verified queued at 00:50:19 Hobart
(14:50:19 UTC on September 5), with two CPUs, 128 GB and a 12-hour limit.
The stage and output roots are new, no-overwrite home-storage locations.
Chrome refreshed the TPAC selector; the existing secure transport helper was
used for SSH/SCP. Raw production data remain remote.

No checks followed queue verification. Await Barry's completion notification
before retrieval and scientific closeout. Q-029 and Q-030 remain open. Changes
are local and uncommitted on `aec8117`; no push or external collaborator message
was sent.
