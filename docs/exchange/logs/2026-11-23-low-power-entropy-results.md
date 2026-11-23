# Completed low-power entropy restarts, 23 November 2026

All seven registered jobs finished successfully. The two switch-on reruns reproduced every compared production fluid value at 11 Myr. The subsequent switch-off allocation ran after both comparisons passed. The terminal job finished at 20:37:36 AEDT. The two simulation allocations used 11,409 allocated core-hours in total. Including preparation, control checks, readout and scoring brings the registered chain to 11,433 allocated core-hours, calculated from PBS walltimes and allocated CPUs. [Submission](2026-11-23-low-power-paired-restarts.md) · [Final PBS accounting](../../science/assets/low_power_entropy_result_2026-11-23/pbs-completion.json)

| PBS job | Completed work | Walltime | Finished (AEDT) |
| --- | --- | --- | --- |
| 883299 | Check production seeds and build four executables | 1:23:00 | 13:29:29 |
| 883300 | Run G-LO and C-LO with entropy recovery on | 3:06:45 | 16:36:19 |
| 883301 | Reproduce the G-LO production control | 0:14:36 | 16:50:57 |
| 883302 | Reproduce the C-LO production control | 0:13:28 | 16:49:48 |
| 883303 | Run G-LO and C-LO with entropy recovery off | 3:15:14 | 20:06:15 |
| 883304[] | Measure 82 distinct native states | 16 workers, all exit 0 | 20:36:47 |
| 883305 | Check native coverage and score frozen forecasts | 0:00:49 | 20:37:36 |

The two build-input manifests for each case differed only in `definitions.h`. The checks covered all 58 source inputs and all 126 historical compiler commands per arm. The output series, final doubles, particle catalogues, source hashes, per-step solver records and score manifests were checked. We rechecked all 84 native inventory entries and the identity of all 164 worker receipts with the corresponding score inputs. [Public audit](../../science/assets/low_power_entropy_result_2026-11-23/independent_verification.json) · [Compact inputs](../../science/assets/low_power_entropy_result_2026-11-23/compact_inputs.zip)

The read-only endpoint measurement 883524[] used the same native lobe definition as the high-power comparison. Its six workers each read the pressure and jet-material fraction in one shared seed or one 12-Myr endpoint. All six finished with exit 0. The two seeds reproduced the production lobe enthalpies and the six pressure hashes matched the energy-budget receipts. [Readout accounting](../../science/assets/low_power_entropy_result_2026-11-23/lobe_readout_pbs.json) · [Endpoint comparison](../../science/low_power_entropy_result_2026-11-23.md)

In the project archive, `turn25_entropy_2026-11-23/` contains the four original solver ledgers, their native companions, the terminal score packet and the source checksums. All 50 selected native files and all 181 score-packet files matched their original hashes after transfer. The unmodified terminal packet (`scored.tar.gz`) has SHA-256 `b215136a6ce8c01c7e988288d4ed7a2d5e3e8a5478c65cf1c50e4a058a5837f8`. The native receipt bundle (`native-receipts.tar.gz`) has SHA-256 `659148e1f3f860233cb3cb710ffa620ab4f97a31277dc340b1bc2ade5d3e4d21`. Both matched the copies in the backup archive. The public ZIP is 593,690 bytes, SHA-256 `02df47c1c377a943883fb6a0211c4de5c38409c4aff334e638396ef7f763f9f7`.
