# Q-029: binary native cocoon and complementary shocked ambient

Status: Q-029 accepted after focused scientific review and repairs; the first
Q-030 Results and figure iteration is ready for supervisor review.

Current caveat (2026-10-21): Q-032 requests Patrick-agent review/action of
the reused X-ray measurements' direct 1%-area mask versus Goal 045's
seed-and-growth geometry. Barry-codex is notified to coordinate corrections.
The native accounting remains accepted, but affected observer-recovery and
downstream interpretations below are provisional pending that review. See
`docs/science/xray_cavity_selection_issue_2026-10-21.md`. Historical numerical
products and acceptance records are preserved, not silently recomputed.

## Scope and acceptance

Barry authorised Q-029 on 2026-09-06. Apply Stas's strict cocoon definition
`float64(tr1) > 0.001` at full cell weight, with exact complementary ambient
membership. Retain fractional weighting and binary `0.005`/`0.01` masks as
sensitivities. Reuse the accepted X-ray-only measurements and the frozen axial
fronts and tracer-independent no-jet calibration. No PLUTO, X-ray, or radio
production rerun is required.

The accepted surface is 19 case-ages: 10/20/30/40/50 Myr for C-HI, C-LO and
G-LO, and 10/20/30/40 Myr for G-HI. G-HI/50 remains excluded. Recompute shock
candidate masks and connected components with the tighter material cutoff;
retain the original entropy/compression, seed, extent, boundary, minimum-cell,
Mach and bilateral gates. Do not require the new censoring counts or energy
fractions to reproduce the old conclusion.

Completion requires the revised native/X-ray and shock comparisons, numerical
closure checks, precision sensitivity and one focused review. It does not
authorise a commit, push, new simulation campaign, or publication. Follow the
standing PBS rule: stop after verified submission and resume on Barry's
completion notification.

## Existing 10 Myr binary result

These are the requested Goal 062 bipolar `>=0.001` values, extracted without
changing the original ledger:

| Case | Volume (kpc³) | Native 2.5pV (erg) | Volume / fractional | Enthalpy / fractional |
| --- | ---: | ---: | ---: | ---: |
| C-HI | 40,186.2701 | 3.491613e59 | 5.9291 | 6.1059 |
| C-LO | 1,137.9835 | 3.981909e57 | 3.8588 | 3.7549 |
| G-HI | 110,230.2107 | 3.144896e59 | 5.3638 | 6.1468 |
| G-LO | 5,120.0590 | 3.879631e57 | 4.5102 | 3.9971 |

Enthalpy is `2.5*(gamma-1)*E_thermal`, with `gamma=5/3`. Exact actual ages and
source paths are in `assets/q029_binary_native_refresh_2026-09-06/existing_binary_10myr.csv`.

## Threshold precision and provenance

Live HDF5 header inspection confirms float32 tracer storage for all 19 native
census inputs. Goal 062's staged `snapshot_energy.py` hash
`eadc395b39446af78c44d4028a8bece21b1c7f3144e8f745a21f7e1e9ce7117f`
matches the committed source, which promotes tracer to float64 before comparing.
No float32 number equals float64 `0.001` exactly, so the stored-value `>=` and
`>` partitions coincide. This establishes reuse under that numerical convention.

It does not establish that no cell contains the float32 representation of
nominal `0.001`: that stored value is `0.0010000000474974513`. The combined
remote pass therefore counts both equality definitions and measures their
volume, mass, pressure-volume and energy contributions. Inspect these ratios
before promoting quantitative conclusions; material precision sensitivity
requires reporting both interpretations and supervisor discussion.

The source binding caught G-HI/10: Goal 062 selected the home continuation
copy, while Goal 067 used the scratch copy. The new wrapper uses the census
source and checks equality of all six required fluid variables, axes and time
between the two copies on the compute node before proceeding.

## Two energy decompositions

For any component density E and current cocoon membership I, preserve the
existing primary allocation:

```
L_absolute = sum(I * E_now * V)
A_allocation = sum(((1-I) * E_now - E_initial) * V)
L_absolute + A_allocation = retained domain energy change
```

`A_allocation` is not the change inside the current ambient region. Also report:

```
B_initial_lobe = sum(I * E_initial * V)
L_region_change = sum(I * (E_now-E_initial) * V)
A_region_change = sum((1-I) * (E_now-E_initial) * V)
L_region_change + A_region_change = retained domain energy change
A_allocation = A_region_change - B_initial_lobe
```

Subtract initial fields before cell summation for regional changes. Evaluate
the allocation through the final identity to reduce background cancellation.
Compute closure from the independent cellwise retained total. Check both
decompositions per energy component and total to `1e-9` of injected energy;
check mass and volume complements to relative `1e-9`. Compare new native rows
against Goal 062 at the same tolerances. These are bookkeeping tests, not a
proof of physical conservation without boundary flux.

The retained t=0 files already contain a nonzero nozzle/tracer region; do not
assume initial tracer is zero. Current absolute lobe energy and current-region
energy change are separate quantities. Enthalpy is never added to the energy
ledger. Shock energy is a subset of ambient-region change, never an additional
term on top of the entire ambient reservoir.

## Shock correction and computation

The old shock integral applied `(1-tr1)` weighting even after selecting cells
with `tr1<=0.01`. Q-029 removes that fractional factor as well as tightening
membership to `tr1<=0.001`. Selected ambient cells contribute their full current
and initial terms. Nonfinite tracer or fluid fields fail before integration;
finite tracer overshoots are counted and retain the existing clipping policy.

Run the native ledger and precision diagnostics during the shock energy read
pass, avoiding a separate reread of the approximately 0.85 TB selected source
files. Kunanyi is appropriate here because the production data are resident
there. Use one 128 GB node, two CPU workers and a 12-hour limit; all derived
output goes to home storage. Synthetic tests run in the allocation before the
production data are processed. Reuse compact no-jet calibration results.

## Native/X-ray comparison

The source-bound compact join preserves all observer measurements and the
37 valid / 20 censored views. Under binary native membership, pressure recovery
remains within a factor of two for 36/37 usable views, volume for 4/37 and
enthalpy for 5/37. Median X-ray/native enthalpy ratios are approximately
0.0222 (C-HI), 0.4938 (C-LO), 0.00603 (G-HI), and 0.0929 (G-LO).

The geometry-dominated recovery pattern remains, but C-LO's former apparent
over-recovery disappears: its median ratio was 6.76 under fractional native
weighting. This is a material case-level interpretive correction. These
comparisons now pass independent native row agreement and threshold precision
review. The revised shock surface retains the same unresolved case-ages.

Products and source bindings are under
`assets/q029_binary_native_refresh_2026-09-06/`. The original Goal 062/066/067
products remain untouched as provenance and sensitivity evidence.

## Submission record

PBS `790871.kunanyi-ohpc` / `q029_native` was verified queued (`Q`) at
2026-09-06 00:50:19 Hobart / 2026-09-05 14:50:19 UTC. Queue: `normal`;
one node, two CPUs, 128 GB, 12 hours. Completion/abort mail goes to Barry.
No subsequent queue checks were made until Barry supplied the successful
completion email on 2026-09-06.

- Stage: `/u/bwbrook/codex_kunanyi/q029_binary_native_refresh_2026-09-06`.
- Analysis: `/u/bwbrook/xray_cavities_analysis/2026-09-06-q029-binary-native-refresh`.
- Expected compact archive: stage root plus
  `q029_binary_native_refresh_2026-09-06.tar.gz`.
- Scheduler logs: stage root plus `q029_binary_native_refresh.out` and `.err`.
- Local evidence: this note's asset directory contains `submission_receipt.json`
  and `staged_inputs.sha256`; upload tar and thin staging tree are ignored
  under `build/`. Source base is `aec8117`, with the submitted changes uncommitted.

All 74 focused local tests passed, alongside shell syntax and diff whitespace
checks. An independent scientific review identified the initial nozzle and
full-cell shock-accounting issues; both were repaired before submission.
Remote preflight verified the upload checksum, all 31 staged file hashes,
shell syntax, and runtime imports under Anaconda3/2024.02-1 (Python 3.11.7,
NumPy 1.26.4, SciPy 1.11.4, h5py 3.9.0, pytest 7.4.0). Allocation-side
synthetic checks and production acceptance subsequently passed (see below).

## Completion and scientific acceptance

The completion email and a single scheduler history check agree: `F/0`,
walltime `02:40:26`, CPU time `04:27:01`, peak memory `41,205,920 KB`.
All four workers exited zero and allocation-side tests reported `51 passed`.
Only the approximately 226 KiB compact archive was retrieved; its SHA-256 is
`08e646b98a2cfd4306a4c50e86a5b35bce8346b00768a55d1ddf6d75f461dfcf`.
Production HDF5 files were not reopened during closeout.

Local revalidation independently accepted all 228 native rows against the
original census, all 19 precision records and the complete source/baseline
binding. The largest component partition residual was `2.30e-14` of injected
energy, well below the `1e-9` gate. At most two cells per snapshot lie at the
single-precision representation of the nominal threshold. Their maximum
volume and enthalpy contributions are `2.39e-7` and `2.57e-7` of the primary
native values. This precision sensitivity is negligible for the selected
science surface. The G-HI/10 overlapping fluid files passed the prescribed
array, coordinate and time equality check.

The primary native enthalpy and shock comparison is:

| Case | Native 2.5pV / injected energy | Selected shock-region change / injected energy | Quantitative shock ages |
| --- | ---: | ---: | ---: |
| C-HI | 0.525–0.559 | 0.666–0.765 | 5/5 |
| C-LO | 0.631–1.108 | 0.223 at 10 Myr | 1/5 |
| G-HI | 0.468–0.498 | 0.505–0.655 | 4/4 |
| G-LO | 0.615–0.785 | 0.580–0.854 | 5/5 |

The tighter ambient definition reduces G-HI shock estimates by 10.0–13.4%
and C-HI by 1.8–8.2%; C-LO/10 changes by −1.0%, and G-LO by −3.7% to +0.12%.
These changes combine the stricter cutoff with removal of fractional ambient
weighting. They do not reverse the selected-region interpretation. The same
four late C-LO ages remain unresolved. Halving/doubling the shock-mask thresholds
is nearly immaterial in G-HI, but matters in G-LO and C-LO/10: at the latter,
energy becomes 1.588 and 0.654 times its primary estimate. These are mask
sensitivities, not confidence intervals.

Native enthalpy is not the regional energy change. Current-cocoon net changes
span 0.132–0.426, −0.160–0.137, 0.425–0.571 and 0.013–0.298 of injected energy
for C-HI, C-LO, G-HI and G-LO. Gravitational changes can be negative relative
to the initial fields. These current spatial regions are not Lagrangian
parcels. Retained whole-domain energy remains above injection, particularly
C-LO (approximately 6–24 times injection); do not treat this as coupling
efficiency. No boundary-flux or native-resolution cellwise no-jet inference
has been added.

The core conclusion survives: native enthalpy is a conditional energy proxy,
X-ray volume/topology dominates its measurement deficit, and an age correction
acts on an energy estimate that is already biased. C-LO's fractional-mask
over-recovery was a native-reference artefact and must not survive in the
primary manuscript argument. Changing the native mask cancels in the three-factor power identity, but
review exposed an older, separate pressure mismatch in the Goal 065 power
tables. The accepted Goal 066/Q-029 observer enthalpies must replace that older
tracer-shell pressure numerator before combining the power and native results.

Accepted products are `accepted_refresh/`, `shock_closeout/` and
`remote_analysis/` beneath this note's asset directory. The final local proof
is `accepted_native_strict_equivalence.json`; the initial header-only proof
remains provenance. `completion_acceptance.json` records the gates and
`shock_change_from_goal067.csv` the historical comparison. The first manuscript
iteration uses these products and the previously validated clock tables.
Q-029 needs no additional raw-data compute. Source changes remain uncommitted;
publication and supervisor sign-off remain separate.

## First manuscript iteration and consistency repair

The focused result review accepted the native/shock conclusions and identified
three reporting repairs, all completed: describe the jointly scaled shock-mask
thresholds (pressure, density and entropy excess), label the shock-to-ambient
allocation ratio explicitly as a non-spatial ratio, and replace stale Goal 065
power numerators with the accepted X-ray enthalpies.

The power repair is local compact-table work. All 74 side-component volumes
and centroid distances match the original age geometry exactly. The sound,
buoyant, refill, shock, true and spectral clocks therefore retain their
existing inputs, side combination and limit status. The changed numerator
replaces tracer-shell pressure with accepted X-ray-deprojected ellipsoid-average
pressure. `build_q029_power_refresh.py` produces 518 power rows, preserving
limits and missing estimates, and checks the three-factor identity to a maximum
relative error of `1.56e-13`. Four focused regression tests pass. For side
clocks, power is the sum of each side's enthalpy divided by its age; the exact
identity uses the corresponding enthalpy-weighted harmonic effective age.

Corrected true-age median power recovery is 0.01218 (C-HI), 0.513995 (C-LO),
0.002919 (G-HI) and 0.072452 (G-LO). Exact mean-pressure spectral subsets give
0.01807 and 0.8562 for C-HI and C-LO. Both group cases remain lower limits only
for that spectral clock. The spectral field convention remains the previously
accepted fractional-tracer global mean-pressure field, explicitly identified
in the manuscript; it has not been silently changed to the binary field.

No further independent audit or raw-data compute is required for this first
iteration. The next scientific review concerns the manuscript argument,
selected figures and whether supervisors want a later binary-field spectral
sensitivity. It is not a publication sign-off.

## Delivered review surface

`manuscript/text/main.md` now contains the first coherent Methods, ordered
Results and Discussion iteration, with three selected figures in
`manuscript/text/figures.md` and `manuscript/figures/`. The surrounding paper
still has explicit drafting placeholders; this is not a complete submission.
The draft PDF/DOCX and submission-profile render are under
`build/manuscript/{draft,submission}/`. Both configuration validation and
`make manuscript-check` passed, including citation and manuscript lint; the
final draft figures and caption page were visually checked. Captions precede
separate figure pages in both profiles to avoid duplicate automatic captions
in the external engine's inline mode.

Reproduce the compact power correction with
`uv run --locked python scripts/science/build_q029_power_refresh.py` into a
new output directory, and the selected figures with
`uv run --locked python scripts/science/build_q029_manuscript_figures.py --force`.
Use `make manuscript-all` for PDF/DOCX rendering. The preliminary compact
native join was moved to ignored `build/q029_preliminary_compact_refresh`;
`accepted_refresh` is the active native/observer surface. The raw returned
products, original historical ledgers, and header proof remain preserved.

Q-029 is analytically complete; Q-030's first iteration is ready for human
review. No commits, pushes, collaborator messages or further remote jobs were
made. The next useful step is supervisor feedback on the argument and figure
selection, rather than another analysis campaign.

## Publication and Stas commit review

Barry authorised commit and push on 2026-09-06. The published review snapshot is
`assets/q029_binary_native_refresh_2026-09-06/xray_cavities_q030_first_iteration.pdf`;
source and three selected figures remain canonical. Raw inputs and temporary
transport archives remain outside Git.

Stas's September 4 commit `cd43b25` (binary cocoon membership) and September 5
commit `8d8740c` (title and Results narrative) are both ancestors of the shared
base `aec8117`. They introduce Q-029 and Q-030, respectively. The accepted
strict-mask native/shock refresh answers the former, including the requested
10 Myr values and equality check. The first manuscript iteration implements
the latter's title, physical-proxy/measurement/clock ordering and consistent
bipolar factorisation. Q-029 is answered and Q-030 is in review; no additional
analysis is required by those commits before supervisor feedback. Optional
radio-power comparison and expansion of the remaining manuscript sections
remain later drafting work, not missing acceptance criteria for this iteration.
