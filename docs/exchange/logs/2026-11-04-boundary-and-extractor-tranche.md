# Boundary comparison and extractor development, 4 November 2026

Barry authorised proceeding with the review recommendations in chat. This
tranche repairs and freezes the BND-02 decision procedure before reading the
full ledgers, retrieves and evaluates those ledgers, measures the prescribed
paired interior cuts, and develops the independent shock diagnostic and
production spherical-budget extractor. No new PLUTO simulation is included.

## Pre-result corrections

The comparison must validate source-bound ledgers, reject malformed face or
time coverage, distinguish incomplete and indeterminate evidence from a
physical refutation, and account for gravitational work, conversion repair
and numerical residuals. The original mass floors and growth range remain
fixed; the amended transport discrepancy uses mass and H+P with a two-sided
10% bound. Accounting contamination has a separately declared 10% budget.
The precise contract is recorded with the comparison implementation and the
dated amendment to the prediction note before full-run measurements are read.

Commit `e56b89f` freezes that contract. The full capture was then taken:
archive SHA-256
`cebd91ce46aa7b3ed7c3c68e8263b7627a0a02dc7a0768de7bad8190c26763a1`.
All 16 files verified both locally and in the project data share. Original
ledgers, receipts and scheduler records are retained outside Git; compact
derived science products are tracked here.

The first comparison stopped during receipt revalidation. Python 3.12's
compensated float summation differs from the target Python 3.11 summation by
one unit in the last place in the cluster outflow hydro transport. That
`4.460149039706125e43 erg` difference propagates into a residual near
`2.109e47 erg`, so a residual-relative receipt comparison was too strict.
The original validator's source hash matches exactly, and left-to-right
summation reproduces the original receipt. The technical correction uses a
bounded rounding allowance for six-face aggregates and propagates that bound
to their residuals; scientific closure and 10% decision thresholds are fixed.
This correction occurred after capture, before scientific contrasts were
inspected. Original receipts remain unchanged.

The interior extractor now measures cellwise absolute background drift in
each twin, reports component-wise 0.01 S(t) tests, and reports mass changes
times initial specific enthalpy plus fixed potential as a contextual energy
equivalent. Paired contrast, grid membership and potential conventions are
unchanged. Local focused validation: 58 tests passed.

The target audit uses a new immutable analysis stage, two CPUs, 16 GB and a
two-hour walltime. The data already reside on the cluster; moving the native
HDF5 payloads to another compute host would add unnecessary transport.
The two smoke pairs qualify the target environment and read-only measurement
path before the full 50-Myr pairs. Scientific failure of a width is retained
as a result, not treated as an execution failure or a reason to widen cuts.

Smoke job `876188` runs that path; full job `876195` is gated on smoke success.
The immutable r1 raw measurement stage precedes the combined-stability label
correction. Its raw sums are retained; the frozen decision overlay verifies
the r1 source/completion/output hashes and supersedes the r1 adoption label.
This avoids repeating native I/O merely to recompute Boolean decisions.

## Results obtained

The frozen comparison supports BND-02 in both atmospheres. At 50 Myr the
cluster/group mass contrasts are `4.76270e43 / 2.29025e42 g`, and H+P
contrasts are `7.00826e59 / 1.21480e58 erg`. Growth exponents on the frozen
five-age grid are `1.96610 / 1.93257`; repair-plus-residual fractions are
`0.0396% / 0.0152%`. Independent reconstruction verified the raw-ledger
identities, source hashes, final contrasts and byte-for-byte derived products.
The paired histories actually share the same step times; the comparison's
independent time alignment remains appropriate but was not needed to resolve
unequal sampling in these particular data.

Smoke `876188` finished F/0 in 21m 44s, including all 58 target tests. Its
capture hash is
`fc2d4c86300fb4f0ce4c27ca4b30af718b41c27d41e143ac265f7cd4217df93f`.
The cluster passes paired localization at 1 kpc, but common background drift
fails through 4 kpc. The group first passes the combined gate at 2 kpc.
Full audit `876195` then started. Detailed result tables and reproduction
commands are in `../../science/paired_boundary_results_2026-11-04.md`.

The 126-row independent shock validation deliberately finishes with
`FAIL_NO_PROMOTION`: all 54 exact-shock rows pass their declared expectations,
but the isentropic sound wave falsely passes the 1.05 arm in all six
placements. The 19 implementation tests pass while preserving this negative
scientific result. No native shock run was attempted.

The production spherical storage extractor is implemented and independently
reviewed, with 11 focused tests including analytic gravitational sign/scale.
Review changed its status contract: completed arithmetic cannot imply a
qualified sphere when the domain is truncated, the candidate boundary-safe
box is crossed, the tracer lies outside [0,1], or native semantic provenance
is still unqualified. Native case/configuration/environment binding remains
the next execution gate; no four-case spherical result is claimed.

## Flux failure discovered during resource check

The previously released job 876162 finished with exit status 1 after 1:02,
at the G-HI early/late source-tree equality assertion. Native dependent
871717 became terminal without running. The continuation root contains no
`src` directory; early and late `pluto` executables and `pluto.ini` files
are byte-identical in the live check. The missing duplicate source tree must
be reconciled with accepted continuation provenance before any replacement
gate is used. No validation gate was bypassed and no scientific flux result
was produced by this failed attempt.
