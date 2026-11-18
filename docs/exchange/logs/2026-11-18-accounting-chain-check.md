# High-power accounting results and outstanding G-LO jobs

At 11:09 AEDT on 18 November, PBS recorded five successful jobs, one failure
and two outstanding jobs in the eight-job accounting chain. The successful
C-LO pair was reviewed on 16 November. The four high-power jobs have since
exited. Their prescribed bipolar power is 2 × 10⁴⁵ erg/s. G-HI uses indices
0–47 and C-HI uses 0–50 from the existing stretched-grid PLUTO histories.

| Job | Case and measurement | PBS exit and wall time | Outputs |
| --- | --- | --- | --- |
| 879904 | G-HI fixed budget | 0, 06:27:27 | All 48 requested snapshots |
| 879905 | G-HI flux | 1, 03:19:52 | Checkpoints 0–46, boundary extrapolation failed at 47 |
| 879906 | C-HI fixed budget | 0, 06:59:48 | All 51 requested snapshots |
| 879907 | C-HI flux | 0, 03:38:24 | All 51 requested snapshots and 50 intervals |
| 879908 | G-LO fixed budget | Running | 36 of 51 snapshot files at the 11:13 AEDT progress check |
| 879909 | G-LO flux | Held | PBS releases its dependency when 879908 exits |

PBS still records completion and abort email for the eight jobs. The G-HI
failure allowed the independent C-HI pair to proceed as scheduled.

## G-HI failure at the last retained snapshot

The flux log records 47 successful snapshot reductions. At index 47,
`measure_q031_fluxes._linear_outer_state` rejected the state obtained by
extrapolating from the two outer cell centres to a domain face. The predicate
checks positive density and pressure and finite primitive values. The log
does not name the failed field or face. The separate fixed-budget job
completed the same index. The failed flux directory contains the bound
request and 47 checkpoints, with no full-run completion record or final
input-stability check. Repeating the same extrapolation on the same inputs
would encounter the same scientific gate. The fixed-budget measurement
also records domain-face contact by traced cocoon cells at 47. This qualifies
interpretation of that retained snapshot. The existing exclusion of snapshots
48–50 still applies.

## What the successful histories show

At 20 Myr the 50-kpc-inset box stores 1.09413 times labelled input in C-HI
and 1.07488 in G-HI. At their respective endpoints those ratios are 0.99986
and 0.93425. The box first misses traced cocoon cells at C-HI index 44 and
G-HI index 40. At the endpoints it excludes 2.63% and 5.55% of the
respective lobe volumes. R100 also extends beyond the inset box from C-HI
index 31 and G-HI index 30. Their later storage differences therefore include
contributions from regions on both sides of the box boundary.

The complete C-HI flux reconstruction gives a negative cumulative balance
outside the nozzle control volume at 50 Myr in every tested scenario,
from −0.12160 to −0.05515 times labelled input. This quantity subtracts
the reconstructed nozzle balance from whole-grid storage change plus
outward transport. Physical loss and realised numerical delivery would
require separate evidence. By comparison the [C-LO reconstruction](../../science/turn18_clo_history_review_2026-11-16.md)
spanned both signs. The original integration and summary routines applied
to the 47 available G-HI checkpoints recover 1,656 interval scenarios.
The cumulative balance is −0.07169 to −0.02759 at 45.99958 Myr across
the 36 choices. An independent integration reproduces both endpoints to
within 1e-12 labelled-input units. The interval from 46 to 47 Myr remains
missing.
All ratios here use the fixed centre-zero potential.

## Evidence and scope

The [compact checkpoint](../../science/assets/turn18_high_power_checkpoint_2026-11-18/accounting_checkpoint.json)
records the dated scheduler states, pinned source and successful completion
hashes, selected fixed-box measurements and reconstructed endpoint ranges.
The fixed-budget arithmetic and geometry audit passed 37,623 checks across
99 snapshots. The largest difference from the earlier spherical energy
components was 9.42e-16 times labelled input. The independent C-HI flux
and G-HI partial-history reductions agree with the values reported above.

The staged producer manifest reverified on Kunanyi. All 236 retrieved regular
files match hashes read independently at the source. The three successes
have the exact requested index sets and all 158 files listed by their
completion receipts (48 + 51 fixed products and 59 C-HI flux products).
The private capture includes those results, the G-HI partial outputs, the
four logs, requests, submission records, source manifest and all eight PBS
records. Comparison with the earlier spherical outputs and the independent
checks of the compact products do not independently repeat native HDF5
integration.

The 238-file capture is archived under
`/data/share/xray_cavities/turn18_high_review_2026-11-18/high_power_accounting_capture_r1.tar.gz`.
SHA-256 on the shared archive matches the local digest
`7ddf50b4018b983b427d9feb62bccfae884c8cc6a5983ff8d90718689931e2a7`.
Extract it into a fresh private directory and run
`(cd stage && shasum -a 256 -c ../stage_files.sha256)` to verify the stage.
The archive contains regular files only. The original stream's references
to native snapshots were omitted from this archive.

The accompanying `high_power_accounting_review_r1.tar.gz` includes the
capture, audit scripts and reports, and earlier input records including the
G-HI inherited lineage receipt. Its SHA-256 is
`0d4f645f0cf89adceef8006de531c8225b0b105262556330a5ccaf5993a8db4c`.
A fresh restoration reproduced all five verification and recovery steps,
including the 17,382 provenance checks. To replay, extract the review at
the project root, extract its nested capture in the private review directory,
and use the project Python environment with the producer sources and tests
at `8177795` and the earlier public spherical measurements present.

```sh
review=private_archive/turn18_high_review_2026-11-18
.venv/bin/python "$review/fixed_audit/audit_fixed_histories.py" --stage "$review/stage/results"
.venv/bin/python "$review/flux_audit/audit_C_HI.py"
.venv/bin/python "$review/flux_audit/derive_G_HI_partial.py"
.venv/bin/python "$review/flux_audit/audit_G_HI_partial.py"
.venv/bin/python "$review/provenance_audit/audit.py"
```

The [17 November energy](2026-11-17-all-case-boundary-injection-audit-request.md)
and [X-ray](2026-11-17-compressive-front-and-background-test-request.md)
requests describe further analyses beyond this eight-job batch.
