# Entropy-switch restart staging, 21 November 2026

The G-HI and C-HI submission bundle is staged and verified on the project's Nectar share. Submission to Kunanyi awaits reactivation of the normal TPAC portal window. PBS has issued no IDs for this experiment. The older injector-history batch, including replacement 882661, is complete.

## Handoff

The private bundle is `turn22_entropy_2026-11-21/paired_release_r5/` on the project share. Its twelve file digests and manifest matched after transfer. The SHA-256 of `SHA256SUMS` is `9092ce6f4f4a52fbf7385a4ac5991a207afe4ce77fc63d36ffc61587325246a3`. The batch wrapper initialises Lmod explicitly and loads the production module versions. Its shell checks passed both with and without a pre-existing module function. Private route information and the notification recipient reside in the existing operations configuration.

Once access is available, confirm the two production roots, original source tree, archive availability and current quota. For both pairs the forecast is **3.91 TiB**, including allowance for an extra full native float per arm, four final double checkpoints, independent restart seeds, particle histories and logs. The one-pair forecast is about **1.96 TiB**. If only G-HI fits, generate the matching one-case contract with the same code and protocol. Keep all outputs and use the allocation with measured space.

Transfer the checksummed bundle to a new control directory and run the following there with the private recipient file and the applicable allocation. The wrapper compares allocated directory usage and filesystem availability to the confirmed ceiling and records the capacity receipt. It queues preparation on hold, registers both controls and dependent runs, verifies PBS mail and dependency settings and then releases preparation. `jobs.tsv` and the submission receipts distinguish a complete submission from a partially registered chain.

```bash
sha256sum -c SHA256SUMS
bash submit_entropy_restart.sh "$recipient_file" "$quota_directory" "$quota_limit_bytes"
```

The full chain comprises preparation, two ON simulations, two 11-Myr comparisons and two OFF simulations. All jobs request end and abort email. If either ON control fails, report the measured difference and leave the OFF results sealed. In local scheduler-fixture tests both OFF jobs depended on both successful comparisons. The preparation hold stayed in place on a wrong mail setting, a missing dependency and a rejected job submission.

## Local verification

Both cases have the same 125 historical compile commands and link command. The preparation contract checks the 117 pinned core files and 50 case-source digests per case, the six production checkpoint fields in double and float, the recorded integrator step and the particle payload. Both manufactured builds restored the same native HDF5 fixture. The passive counters reproduced the uninstrumented states and took separate signed measurements of entropy changes and pressure repairs. Actual cluster compilation, checkpoint validation, 11-Myr replay and simulation results remain pending. [Acceptance criteria and native verification receipts](../../science/entropy_restart_protocol_2026-11-21.md)

The prior production files also resolve the normalisation and gravity questions raised in board message 3615. Matching each numerator to signed injector delivery changes the primary native lobe fractions, with C-LO remaining below unity at the selected ages. C-HI's signed gravitational work accounts for 32.8% of its exterior deficit at 10–12 Myr and 51.9% at 29–30 Myr. The local tracer partition places much of the near-injector imbalance in partially marked gas. Identifying the operation that changes the gas energy requires the staged experiment. [Energy fractions](../../science/native_delivery_restatement_2026-11-21.md) · [Localisation and gravity comparison](../../science/entropy_localisation_2026-11-21.md)
