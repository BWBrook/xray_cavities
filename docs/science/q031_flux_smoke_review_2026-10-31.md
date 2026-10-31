# Q-031 first retained-output flux review — 31 October 2026

This review covers G-LO snapshots at 0 and 0.9996596844404672 Myr only.
It does not establish the four-case energy budget, C-LO boundary explanation,
or later-time nozzle delivery. No new simulation was run.

## Execution and integrity

PBS 870352 completed both numerical snapshots in 208.667 and 296.194 seconds,
passed all 15 synthetic/provenance tests and wrote the completed science receipt.
It then failed with exit 1 when the recursive tar step reported
`results_smoke: file changed as we read it`. Dependent job 870353 was cancelled
without starting the four-case measurements. Preserve both as failure provenance.

The downloaded original archive has SHA-256
`256416fa6dcacce7e4c61842c6d607a04acbeb90fa7de752831d5f59d2c2b25f`.
All four scientific output files match their case manifest and the completion
receipt names G-LO. The parent independently recomputed 144 mass/energy storage,
integrated flux and inferred-source values from the instantaneous and storage
CSVs; all agree within relative tolerance 2e-13.

The first real snapshot's flux and storage rows match the earlier direct-read
implementation exactly, excluding only the different stage-local input symlink
path. Its runtime fell from 433.087 to 208.667 seconds in these two runs, though
cache warmth and shared filesystem load prevent treating this as a controlled
benchmark. The two-snapshot job peaked at 627,928 KiB RSS.

## Numerical findings

Nominal bipolar injection over the interval is 6.30937209154e56 erg. The
whole-grid thermal, kinetic and gravitational changes are respectively
3.87958697629e56, 2.96759622582e56 and 4.52768350785e54 erg; total
6.89246003719e56 erg, or 1.09242 times nominal injection.

| Reconstruction / quadrature | Inferred source / nominal |
| --- | ---: |
| Whole grid, outer active cell, left / trapezoid / right | 1.09242 / 1.08219 / 1.07197 |
| Whole grid, linear boundary, left / trapezoid / right | 1.09242 / 1.07600 / 1.05958 |
| Nozzle controls, all padding/reconstructions, trapezoid | 0.53482–0.55793 |
| Nozzle controls, all padding/reconstructions, left rectangle | 0.01159–0.02807 |
| Nozzle controls, all padding/reconstructions, right rectangle | 1.05804–1.08779 |

The preferred outer-active trapezoid estimates net boundary inflow of
6.4507354746e+54 erg, or 0.010224 times nominal injection. This reduces the
whole-grid excess from 9.24% to 8.22%; it does not close the first-interval
balance. Linear extrapolation implies more inflow, 0.016416 times nominal.
These are reconstruction sensitivities, not confidence intervals.

The padded nozzle surfaces have zero saved flux at t=0. By the next snapshot,
their outward energy rates are 1.04645–1.05972 times the configured bipolar
power. A trapezoid between those endpoints therefore counts about half of a
roughly steady final rate. With no saved intermediate startup history, neither
the left, trapezoid nor right rule determines the true integrated delivery.
The 0.535–0.558 ratios do not establish half-power injection, and the near-unity
right rectangles cannot be selected as a closure correction. Storage changes
are included in every estimate; the initial saved state already contains the
nozzle overwrite.

The cumulative outermost cell layer gains 2.62666e55 erg, while the outer eight
layers gain 6.69927e54 erg. Signed storage changes can cancel between layers;
this is not a monotone measure of cumulative boundary heating.

## Packaging repair

The r5 wrapper keeps the science runner and its source hashes unchanged. A
packaging helper selects completion.json, each case manifest and its four
manifested scientific files, excluding live logs, tests, input symlinks and
checkpoints. It verifies exact archive membership, sizes and hashes against the
hashes accepted during validation, then writes a receipt. Outputs are exclusive.
A post-validation same-size mutation is rejected. Eighteen combined flux and
packaging tests pass; the helper also successfully repackaged these actual
completed smoke files locally.

The recovery allocation revalidates the existing r4 smoke and packages it under
a fresh r5 stage. It does not repeat the two measurements. The full replacement
job must depend on successful recovery and migration, and retain all migration
completion gates. Scheduler receipts and final job IDs are recorded in the
exchange log.

## Next scientific gate

Inspect the complete four-case histories, especially later adjacent snapshots,
before interpreting cumulative source delivery. Compare temporal quadratures,
nozzle padding, face reconstructions and whole-domain balances without choosing
a sensitivity to force agreement. The spherical-aperture and no-jet audits
remain open.
