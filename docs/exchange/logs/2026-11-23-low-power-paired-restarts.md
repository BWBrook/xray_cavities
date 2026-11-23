# Low-power entropy-switch restart pairs, 23 November 2026

Barry approved the C-LO and G-LO switch-on and switch-off restarts from the production 10-Myr checkpoints to 12 Myr. The estimated cost of the four arms together is 13,000 core-hours. The protocol and evaluator were frozen before either control ran. [Approval](../../correspondence/thread-0029.md#message-3678--codexmini-gpt-6--decision) · [Forecast and checkpoint identities](../../science/low_power_entropy_restart_protocol_2026-11-23.md) · [Scoring code](../../../scripts/science/score_low_power_entropy.py)

## Simulation and measurement

At 12:07 AEDT on 23 November, preparation was running and each successor was waiting for its prerequisites. PBS had the correct recipient and end and abort notifications on all seven jobs. The retained 4.30 TB forecast fit both the project allocation and the filesystem. [Scheduler, storage and source verification](../../science/assets/low_power_entropy_restart_2026-11-23/submission.json)

| PBS job | Work | Successful prerequisite |
| --- | --- | --- |
| 883299 | Prepare both checkpoints and build the four executables | Released after submission checks |
| 883300 | Run G-LO then C-LO, switch on | 883299 |
| 883301 | Compare G-LO with its 11-Myr production state | 883300 |
| 883302 | Compare C-LO with its 11-Myr production state | 883300 |
| 883303 | Run G-LO then C-LO, switch off | 883301 and 883302 |
| 883304[] | Measure storage and fluxes on native outputs | 883303 |
| 883305 | Verify native coverage and score the frozen forecasts | All 16 workers in 883304[] |

Both checkpoint doubles contain six full-grid float64 fields. Each seed's integrator record identifies its float field and particle file. The submission preflight compared both production executables, six runtime files, 100 case-setup files and 117 shared source files against their recorded SHA-256 sums. Each arm uses the production layout of 1,792 MPI ranks. Each switch-on control compares its 11-Myr state with the original run. Both controls must pass before either switch-off simulation starts.

After the four simulations, a 16-worker array measures 82 distinct saved states. Its tasks include each common seed once and 20 subsequent outputs per arm. A final job checks the native catalogue and stage coverage and scores the signed solver counter and independently reconstructed exterior energy balance. The two 1-Myr switch-on forecasts and the 19 post-startup switch-off intervals use the low-power bipolar label of $2\times10^{43}$ erg s$^{-1}$. The packet retains the first interval, gross gains and losses, and the signed 1-Myr and 2-Myr results. [Task assignments](../../science/assets/low_power_entropy_restart_2026-11-23/readout_tasks.tsv) · [Submitted readers](../../science/assets/low_power_entropy_restart_2026-11-23/readout_inputs.sha256)

The project archive holds the source probe, integrator records and submissions in `turn24_entropy_2026-11-23/native_submission_inputs.tar.gz`. Both archive copies have SHA-256 `7d1dcd488b7e371555cc2507d2f39ffbb09d5d6fa975e1cccf088686fb4c1b41`. The high-power lobe readout uses retained outputs from the previous experiment. [High-power measurements](../../science/entropy_restart_lobes_2026-11-23.md)
