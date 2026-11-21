# Entropy switch and the energy balance outside the injector

The experiment asks how much of the measured energy shortfall disappears when PLUTO evolves the same jet with its selective entropy switch disabled. The primary case is G-HI. C-HI supplies a second atmosphere on the same grid if the allocation can hold both pairs. The authorisation recorded in board message 3616 covers these restarts.

## Starting states and retained outputs

| Case | Checkpoint, Myr | Production step | Original 11-Myr control step | Primary production exterior residual over 10–12 Myr |
| --- | ---: | ---: | ---: | ---: |
| G-HI | 9.99926 | 10011 | 10990 | −0.09213 |
| C-HI | 9.99989 | 10183 | 11159 | −0.04615 |

The checkpoint is double-HDF5 index 2, float index 10, particle index 1000 and the matching integrator record. G-HI's archived 11-Myr comparison comes from the production continuation that resumed from this checkpoint. C-HI's comparison comes from the uninterrupted production run. Preparation verifies the binary and configuration identities, the particle records and time, and the six double-checkpoint fields rounded to the independently identified native float output.

The seed comparison uses the production writer’s float conversion, including its flush-to-zero mode. This was verified after the initial preparation stopped on tiny C-HI tracer values. Each full field still has to match cell by cell. The correction applies to the 10-Myr file representation, before the simulation or the independent 11-Myr test. [Native conversion verification](assets/entropy_restart_protocol_2026-11-21/seed_validation_repair.json)

Each pair runs to 12 Myr on 1,792 MPI ranks. Both arms keep all six native fluid fields at 0.1-Myr cadence, the original particle cadence and the final double checkpoint. PLUTO tests for output crossings without shortening intermediate hydrodynamic steps. Both arms inherit the same production runtime inputs, isolated source copy, compiler commands, MPI launcher and measurement code. The two source manifests must differ only in the value of `ENTROPY_SWITCH` in `definitions.h`. Retain the original executable digest, both new executable digests, compiler/module details and the native storage receipts.

The two historical production build logs contain the same 125 compilation commands and final link. The release checks all 126 commands, both executable wrapper paths and 117 pinned core source and build files. G-HI also has historical checksums for the double and particle checkpoint. For C-HI the staging job measures the two checksums and compares against its previously identified float file and particle structure.

## Control before interpretation

Each selected ON arm must finish, and its 11-Myr comparison must pass, before either OFF arm starts. PBS schedules both ON cases in sequence in one allocation and the two comparisons as separate jobs. The OFF allocation depends on both comparisons succeeding. Each OFF arm also reads both comparison receipts at startup. The gate reads the canonical production file by SHA-256, compares the grid and all six fields, checks positive density and pressure, and requires the sum of particles restored on all ranks to equal the checkpoint count. The time and step must match to within one production hydro step. [Submitted jobs](../exchange/logs/2026-11-21-entropy-paired-restart.md)

Two tolerances were set before running. In the union of cells with tracer above 0.001 or speed at least 100 km/s in either state, the volume-weighted L1 difference must be at most 1% of the original norm for **each** primitive field. Across the entire mesh the sum of absolute cellwise changes in **each** of thermal, kinetic and fixed-potential energy must be at most 0.5% of the labelled 10–11 Myr input. Taking absolute differences before summation prevents compensating errors in different cells from passing the gate. A failed control stops interpretation. [Control implementation](../../scripts/science/check_entropy_restart_control.py)

## Predictions and diagnostic

Use the primary exterior residual from the existing accounting pipeline, whole-grid source minus net injector delivery with the same control-volume storage convention, divided by the labelled input over the interval. Report each short interval and the duration-weighted 10–12 Myr balance. Compute the fraction of the deficit removed relative to the measured ON arm. Report the alternative time and face-integral choices and the reconstructed injector delivery separately.

Claude forecast −0.06 to −0.08 for G-HI ON. The archived 10–11 and 11–12 Myr values are −0.0910 and −0.0933. Preserve the forecast and score the control against its archived state. For G-HI OFF, a residual of magnitude at most 0.01 supports the proposed explanation. A remaining deficit of 0.05 or larger refutes it as the explanation specified in message 3616. An intermediate deficit gives a partial effect. A positive overshoot above 0.01 needs separate interpretation. Use C-HI's own control as the comparator for its change. The injector is predicted to deliver about 1.15 times label in both arms. [Existing interval measurements](entropy_localisation_2026-11-21.md)

The diagnostic counts physical-cell visits at each accepted RK2 stage. It measures signed changes in conserved gas energy when pressure comes from entropy and on the negative-energy and pressure-repair branches. It also records density repairs and their mass. Use weights ½ and 1 for the two stages, keep gross and signed changes, and sum by fixed radius and tracer concentration at the time of the operation. For a cell that undergoes both an energy floor and an entropy repair, the latter starts after the first repair. If a run stops, the ledger contains only completed RK steps. Report the exit, native failure location and finite coverage before attributing any imbalance. [Solver patch and SHA checks](../../scripts/kunanyi/patch_entropy_restart.py) · [Manufactured RK and pressure-floor checks](../../scripts/kunanyi/verify_entropy_restart_diagnostics.py)

The production histories alone already place a 2.25-percentage-point deficit between 0.75 and 0.85 kpc in G-HI at 10–12 Myr. A further 6.96 points lie outside 0.85 kpc. The native stage measurements test whether and where the entropy update can account for either component. [Radial and tracer balances](entropy_localisation_2026-11-21.md)

## Verification before submission

The instrumented native RK and mapper kernels preserved the final state and flags bit for bit within each switch configuration in the manufactured tests. Signed changes agreed with a separate scalar calculation in all 44 occupied stage/location bins. The two native restart readers reproduced all 84 stored test values, time, step length and step number from the same manufactured HDF5 checkpoint. These receipts cover the local serial tests. The MPI production replay remains the acceptance test. [RK checks](assets/entropy_restart_protocol_2026-11-21/native_rk_verification.json) · [Shared-checkpoint checks](assets/entropy_restart_protocol_2026-11-21/shared_hdf_verification.json)
