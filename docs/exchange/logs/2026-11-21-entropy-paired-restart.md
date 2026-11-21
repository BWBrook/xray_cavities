# Entropy-switch restart submission and recovery, 21 November 2026

## Replacement jobs, 17:06 AEDT

Preparation 882687 failed after 38 min 50 s at the comparison of C-HI’s 10-Myr double checkpoint with the independently identified single-precision output. PBS cancelled 882699 before execution. The two comparisons and switch-off job stayed held, and were retired after their accounting records were saved. None of the initial four simulations started. Both original production histories and the failed staging area are retained.

| PBS ID | Work | State at 17:06 AEDT | Successful prerequisite |
| --- | --- | --- | --- |
| 882758 | Validate seeds and build four executables | Running | Released |
| 882759 | G-HI then C-HI, switch on | Waiting | 882758 |
| 882760 | G-HI at 11 Myr against production | Waiting | 882759 |
| 882761 | C-HI at 11 Myr against production | Waiting | 882759 |
| 882762 | G-HI then C-HI, switch off | Waiting | 882760 and 882761 |

The two archived executables have the same digest. Their startup code sets MXCSR bits `0x8040`, enabling flush-to-zero and denormals-are-zero. Their HDF5 writer calls the native double-to-float conversion with a unit factor of one. Ordinary NumPy conversion preserved **10,183** tiny nonzero tracer values in the four-plane slab beginning at index 184. The production single-precision file recorded zeros for all of them. The archived double values ranged from about 7.01 × 10⁻⁴⁶ to 1.17 × 10⁻³⁸. [Intel’s floating-point mode reference](https://www.intel.com/content/www/us/en/docs/fortran-compiler/developer-guide-reference/2026-2/set-the-ftz-and-daz-flags.html)

The repaired reader reproduces the native cast and continues to require numerical equality cell by cell. A 21-value x86 test established the rounding boundary. A second check compared 34,352 output bit patterns, including both signs and adjacent representable doubles at the transition to the smallest normal float. All matched. The entire failing slab and six-field central samples from both original production file pairs passed. Regression tests reject a one-ULP normal discrepancy, an unexpected subnormal, a missing normal value and nonfinite data. Full-field comparisons for both seeds run in 882758 and record counts by field. The 11-Myr thresholds, original double seeds, production source contract and both simulation arms match the first submission. The new work root is separate. PBS verified both dependency links into the switch-off allocation, all rank requests and end/abort notifications for the existing recipient. [Failure, native conversion and replacement submission receipts](../../science/assets/entropy_restart_protocol_2026-11-21/seed_validation_repair.json) · [Reader](../../../scripts/kunanyi/stage_entropy_restart.py) · [Regression checks](../../../tests/test_entropy_restart_checkpoint.py)

## Original submission, 12:50 AEDT

Kunanyi accepted both authorised G-HI and C-HI pairs at 12:50 AEDT. At 12:51 AEDT preparation was running and the other four PBS jobs were waiting for their prerequisites. The switch-on runs must each reproduce their own 11-Myr production state before either switch-off run can start.

### Original PBS jobs

| PBS ID | Work | Must finish successfully first |
| --- | --- | --- |
| 882687 | Validate restart seeds and build all four executables | None |
| 882699 | Switch on, G-HI then C-HI | 882687 |
| 882700 | Compare G-HI at 11 Myr with its original production file | 882699 |
| 882701 | Compare C-HI at 11 Myr with its original production file | 882699 |
| 882702 | Switch off, G-HI then C-HI | 882700 and 882701 |

Four separate 1,792-rank reservations require 7,168 CPUs. The normal queue caps queued requests at 7,000 CPUs per user. Initial registrations 882688–882691 were withdrawn while held, before they ran. Each replacement simulation job requests 64 nodes with 28 ranks per node for up to 20 hours. Each case runs separately across the whole allocation and retains its own logs, exit status, particle history and 0.1-Myr fluid outputs. A failed control blocks the switch-off allocation. After both controls pass, a G-HI switch-off solver failure is recorded and C-HI can still run if the allocation is live. [Allocation wrapper](../../../scripts/kunanyi/entropy_restart_cases.pbs)

Before release we read all five records back from PBS and checked the dependencies, CPU requests, mail options and private recipient. PBS recorded end and abort notifications for each job. Each two-case simulation allocation generates one completion notification. [Scheduler receipt](../../science/assets/entropy_restart_protocol_2026-11-21/pbs_submission.json)

## Inputs and storage

All twelve files in the frozen r5 bundle matched their digests on Kunanyi. The SHA-256 of `SHA256SUMS` is `9092ce6f4f4a52fbf7385a4ac5991a207afe4ce77fc63d36ffc61587325246a3`. The allocation wrapper staged alongside it has SHA-256 `d3c51633c3ab500ff5e06788d0c211ffe975bedeb69e23eb81f51fe4f8e79a70`. All 225 live core, case-source, runtime and executable checks passed. The 10-Myr double, float and particle seeds and the 11-Myr comparison files were present for both cases. Preparation performs the full native checkpoint and particle validation.

The four-arm forecast is 4,296,730,891,728 bytes (3.91 TiB). The scratch quota is 8 TiB with 216,774,144 bytes allocated before preparation. The private project archive retains the capacity calculation, input checks and initial and final registration lists.

## Local verification

Both cases have the same 125 historical compiler commands and link command. Both manufactured builds restored the same native HDF5 fixture. The passive counters reproduced the uninstrumented states and measured the signed entropy changes and pressure repairs separately. Scheduler fixtures verified that an incorrect mail setting, missing dependency or rejected submission keeps preparation held. Case-runner fixtures checked control failure and independent switch-off failures. The native 11-Myr replays and the switch-off measurement remain pending. [Acceptance criteria and native verification receipts](../../science/entropy_restart_protocol_2026-11-21.md)

The prior production files also resolve the normalisation and gravity questions raised in board message 3615. Matching each numerator to signed injector delivery changes the primary native lobe fractions, with C-LO remaining below unity at the selected ages. C-HI's signed gravitational work accounts for 32.8% of its exterior deficit at 10–12 Myr and 51.9% at 29–30 Myr. The local tracer partition places much of the near-injector imbalance in partially marked gas. Identifying the operation that changes the gas energy requires the staged experiment. [Energy fractions](../../science/native_delivery_restatement_2026-11-21.md) · [Localisation and gravity comparison](../../science/entropy_localisation_2026-11-21.md)
