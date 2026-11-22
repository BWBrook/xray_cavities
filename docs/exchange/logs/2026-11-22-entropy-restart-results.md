# Paired restart outputs, 22 November 2026

The G-HI and C-HI switch-on and switch-off restarts used the release and dependencies in the [original submission and repair record](2026-11-21-entropy-paired-restart.md). The table gives the PBS exit code and actual walltime for the repaired chain.

| PBS job | Work | Exit | Walltime |
|---|---|---:|---:|
| 882758 | Validate checkpoints, build both executables and stage both pairs | 0 | 1 h 33 min 17 s |
| 882759 | G-HI and C-HI with entropy switch on | 0 | 3 h 23 min 44 s |
| 882760 | Compare G-HI with the 11-Myr production output | 0 | 12 min 24 s |
| 882761 | Compare C-HI with the 11-Myr production output | 0 | 12 min 28 s |
| 882762 | G-HI and C-HI with entropy switch off | 0 | 3 h 46 min 38 s |

Read-only PBS array **883167** finished at 23:50 AEDT. Its parent and all 16 workers have final state F and exit 0. All 82 grid and 82 injector measurement receipts matched their remote SHA-256 after transfer. The compact public archive has SHA-256 `3ba5fa77d79d9f43e125f04a1d026206ce2c5127c1ed1c9be671ea3f284d882b`. A clean extraction reproduced all six energy tables byte for byte. A second implementation checked the raw signed solver records, the original control measurements and all four primary budgets. [Array accounting](../../science/assets/entropy_restart_result_2026-11-22/readout-pbs.json) · [Independent verification](../../science/assets/entropy_restart_result_2026-11-22/independent_verification.json)

The four arms each restored the shared checkpoint on 1,792 MPI ranks, produced 20 new full-grid float snapshots and reached the final 12-Myr double checkpoint. Each particle series has 201 files including its seed. The final doubles are 67,318,639,276 bytes each. Their native catalogue times, lengths and integrator steps were verified. The two switches' 58-file build-input manifests differed only in `definitions.h` within each pair. [Controls, compiler identities, native inventory and stage evidence](../../science/assets/entropy_restart_result_2026-11-22/compact_inputs.zip)

The retained compact native archive is `turn23_entropy_2026-11-22/native-receipts.tar.gz` in the project archive. Its local and backup copies have SHA-256 `5b44a2562b1b2bbfac5d2736594dc0e53d5a6e105a58d9cb7586c48368f7115c`. It contains the four raw stage ledgers, control and restart receipts, catalogues and simulation accounting. Its 52 member digests were checked after retrieval. The large native checkpoints and float outputs remain in simulation scratch.

The read-only postprocessing array measures each distinct saved state once. It reads all five hydrodynamic fields across the whole grid, all six fields in the injector neighbourhood and each domain face. The incoming and outgoing rates, component stocks and five field digests survive in each compact measurement. The initial snapshot serves both arms of its case. All ten reader and wrapper files match the submitted manifest. Its digest is `a1f4d2b51a3c53c8bba1215be8bb7c87a03b73a847f94a241c59453c54037dee`. [Submitted hashes](../../science/assets/entropy_restart_result_2026-11-22/readout_inputs.sha256) · [Task assignments](../../science/assets/entropy_restart_result_2026-11-22/readout_tasks.tsv) · [Scientific results and public replay](../../science/entropy_restart_result_2026-11-22.md)
