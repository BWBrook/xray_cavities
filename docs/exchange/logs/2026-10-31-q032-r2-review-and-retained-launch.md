# Q-032 r2 review and retained-view launch

Barry said “Back to you; Claude's reply is on the Board.” Codex read discussion
29 message 2688, refreshed main to `7da6ed5`, independently reviewed the
corrections and staged the retained-map diagnostic. Replies are 2696, 2697
2699 and 2702. No production detector, topology policy or dependent energetics
was adopted or refreshed.

## Corrected synthetic evidence

The independent reviewer verified the environment-input, r1 and r2 manifests,
and reproduced 1,984 rows across 124 scenarios, the null detections, reported
rim medians, Mach 1.5 jumps (density 12/7, temperature 1.4947917), and stratified
mass quadrature. The review suite reported 23 passed and one expected strict
xfail. Refined mass-matching quadrature stayed within about 1.3e-5 of unity.

Claude withdrew the r1 cluster–group contrast after correcting isobaric rims
that had been described as isothermal. At a = 40 kpc, reported oracle
seed-and-grow recovered/true volumes for cluster/group are approximately:

| Shell prescription | Cluster | Group |
| --- | ---: | ---: |
| Isobaric x2 | 0.36 | 0.90 |
| Isothermal x2 | 0.24 | 0.28 |
| Mach 1.5, width 0.15a | 0.54 | 0.35 |
| Mach 1.5, mass matched | 0.28 | 0.08 |

These demonstrate shell-prescription sensitivity. The observer radial
background can also select off-cavity sky when bright rims raise the azimuthal
median. Neither effect establishes the correction for actual simulated shells.

The remaining physical qualification is material: expanded shells around the
touching bipolar cavities overlap, including intrusion into the opposite
cavity. The overlap is about 5.1–5.7% of each grown outer spheroid for the
mass-matched widths. The renderer adds separate emissivity perturbations rather
than forming a single local density/temperature state. “Mass matched” therefore
describes additive per-lobe bookkeeping, not a self-consistent shocked shell.
This was returned to Claude along with stale component-table counts/wording.

The proposed narrow-neck topology rule remains a separate validation arm. It
needs predeclared physical/grid scaling and tests on touching/detached pairs,
single deficits, bright bridges and null residuals before production use.

## Retained-view diagnostic

PBS `870640.kunanyi-ohpc` was submitted and observed `Q` at
2026-10-31 09:58:30 UTC, then `R` at 09:59:03 UTC on n007. Resources are
normal queue, 2 CPUs, 8 GB, four hours. It uses the 60 existing home-storage
views independently of the unfinished scratch migration.

Stage:
`/u/bwbrook/codex_kunanyi/q032_retained_method_ladder_2026-10-31_r1`.

The source base is `7da6ed5`, plus the staged wrapper/validator and the small
strict-reference correction described below; exact hashes, not the base commit
alone, identify submitted code. Upload SHA-256:
`01e87948e62ac9ac933ab9c509400221afe67777f2b107773d107a463458c407`
(496,330 bytes). Remote checksum verification passed for all 19 staged files.
The portal reported an upload error, but the remote byte hash matched; no
duplicate upload was attempted.

Five runs per view: legacy area 1%, observer seed-and-grow, and radial-background
deficit thresholds 0.05/0.10/0.20. There are no t0-baseline runs because matched
initial-state renders are not yet supplied. The runner's tracer evaluation
mask was corrected from `>= 1e-3` to strict `> 1e-3`, including its metadata.
The round-trip test now checks values below, equal to and above the threshold.
Observer masks are unchanged. All 21 focused tests passed locally after the
correction and on Kunanyi (114.32 s), observed at 10:00:48 UTC while the job
remained running. Independent review approved the wrapper; shell syntax and Python
compilation passed, and a generated fixture exercised 300 inputs, 600 rows and
124 archived members end to end.

The wrapper binds 300 input files before and after; requires exactly 60 views,
600 rows, 60 packed-mask products and 60 stamps; verifies all manifest and
archive members; and creates a final provenance receipt. Topology-rejected
measurements remain labelled. G-HI/50 is included for evaluation while its
existing scientific exclusion remains. Partial products do not establish
completion. Retain the external input bindings, validation, stage manifest,
receipt and logs alongside the results-only archive when retrieving results.

Local submission evidence is under
`docs/science/assets/q032_retained_method_ladder_2026-10-31/`.

## Other work and next gate

At 09:51 UTC, migration `870323` was running after 6:00:23 and full flux
`870374` was held behind recovery/migration success. Neither has new completed
scientific results from this check. No migration files were modified, and no
quota recovery is claimed. One later log inspection used a nonexistent filename;
that inspection error says nothing about migration progress.

The proposed next native extraction is in
`docs/science/q031_native_path_length_design_2026-10-31.md`. It preserves strict
cocoon/ambient definitions, valid shock status, matched projection geometry and
cellwise emissivity rather than relying on mean density/temperature. This is
design for methodological review, not an implemented or submitted native job.
No scheduled checks were created.
