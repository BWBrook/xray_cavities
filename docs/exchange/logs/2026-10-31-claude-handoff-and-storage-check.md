# Claude handoff, boundary audit and storage inspection — 31 October 2026

Barry said “Back over to you from Claude.” Codex read Correspondence discussion
29 message 2644, confirmed file ownership in message 2647, and completed this
bounded evidence/handoff tranche. The shared Git base was `8ea3294`; prior
local migration work was preserved. No production analysis was replaced,
no PLUTO job was launched and no migration resume was submitted.

## Remote inspection

Direct `kunanyi-via-nectar` reached the TPAC jumpbox but required interactive
authentication. The existing authenticated Open OnDemand portal shell supplied
the inspection without changing credentials or access configuration.

`scripts/kunanyi/inspect_xray_handoff_state.py` ran on `kunanyi-00`, reading
metadata, small coordinate/metadata files and existing receipts. Its only write
was a new inspection JSON, created exclusively at
`/u/bwbrook/codex_kunanyi/scratch_home_migration_2026-10-16/handoff_inspection_2026-10-31.json`.
The portal download has the same 298,863 bytes and SHA-256
`dcc6ce2d7e2fc08cce4beb13328ede607dd5d1ca757921411542207cd7f29d6d` as the remote
file. It records observation time `2026-10-31T00:33:21.683516+00:00`.
Local JSON, derived file inventory and checksum manifest are in
`docs/science/assets/q031_q032_handoff_2026-10-31/`.

PBS `820961.kunanyi-ohpc` is `F/271`; it used `48:01:51` against a `48:00:00`
limit and ended on 18 October at 22:54 AEDT. The separately read `migration.err`
says `=>> PBS: job killed: walltime 172911 exceeded limit 172800`.

| Frozen plan units | Observed state |
| --- | --- |
| First eight, through the 20 August G-HI production tree | `complete`; expected source links, live destinations and policy receipts; no tombstones |
| 17 August C-HI full-history rerun | `copied`; original scratch directory and archive copy present; no tombstone or completed policy receipt |
| 17 August C-LO full-history rerun | No state record; original scratch directory present; destination absent |

Completed-unit receipts total 2,606,334,382,194 logical payload bytes. This is
not a fresh quota measurement or a new hash audit of those payloads. The remote
`stage_checksums.sha256` matches the retained local acceptance copy. Resume
must reuse the frozen plan, source and state after active-job and receipt
checks; it must not bypass verification of the C-HI copy. The existing source
supports signature-bound reuse of durable completed-file hash receipts.
No scheduled checks were created.

## Retained map inventory

Let `BASE=/u/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables`.
These are separate home analysis trees, not the archived scratch-analysis unit.

| Case | Case root below BASE | Required files | Bytes |
| --- | --- | ---: | ---: |
| C-HI | `xray_cavity/c_hi` | 90 | 496,855,489 |
| C-LO | `xray_cavity/c_lo` | 90 | 496,855,460 |
| G-HI | `xray_cavity_g_hi_r2/g_hi` | 90 | 496,855,616 |
| G-LO | `xray_cavity/g_lo` | 90 | 496,855,585 |

All 60 age/view bundles exist: ages 10/20/30/40/50 Myr and views 0/45/90°.
Each `age_NN/xraise_grid_Vdeg/` contains corrected X-ray brightness,
`tracer_max_los.tsv`, horizontal and vertical coordinate TSVs, metadata JSON
and summary CSV. Horizontal coordinates are `x_kpc.tsv` at 0° and `u_kpc.tsv`
at other views. The total is 360 required files and 1,987,422,150 bytes.
G-HI/50 is retained for X-ray evaluation despite its native shock censoring.
All 20 source-manifest HDF5 paths exist, including compatibility-link resolution
where applicable. No `age_00` directory exists in these four roots; this is
not an exhaustive search for every historical t=0 product.

The inspection hashes the small coordinate/metadata files, not the 120 large
brightness/tracer maps or native HDF5. Presence and sizes do not validate pixel
values. No pixel maps were downloaded to the mini in this tranche. The local
previous selected-age bundle contains only compact summaries and plots.

## Work ownership and interface

Claude owns the Q-032 recovery, seed/grow, selected-age X-ray cavity/pressure,
deprojection, topology, validation and method-comparison scripts, their tests
and new `docs/science/q032_*` notes. Codex owns Q-031 native energy/shock,
whole-grid and selected-age native/dual-space scripts, the cluster background
diagnostic, `scripts/kunanyi/`, their tests and `docs/science/q031_*` notes.
Codex is the current writer for `HANDOFF.md` and `current_status.md`.
Coordinate cross-owned helper changes before editing. Manuscript and registry
changes wait for reviewed results from both streams.

The first comparison is legacy 1%, validated seed-and-growth and one
null-calibrated deficit threshold, with observer and t=0 backgrounds where
available. The latter is a projected emission-deficit reference, not a unique
3D truth volume. Radio geometry remains a labelled multiwavelength comparison;
CADET requires a domain assessment. Pressure recovery needs its own validation.

The proposed new path-length NPZ interface uses the exact X-ray grid, pixel
edges/view transform, units, source hashes, case/snapshot and mask definitions.
Use explicit `cocoon`, `shocked_ambient` and `ambient_total` semantics: shocked
ambient is part of the tracer complement, not a disjoint third component.
Derive unshocked ambient only where the shock classification is valid. An
invalid/rejected shock age must remain labelled unavailable, not encoded as
zero path length. This clarification was sent for Claude's agreement; no NPZ
path-length product has yet been implemented.

The Q-031 source/numerical audit and its limits are recorded separately in
`docs/science/q031_boundary_hypothesis_2026-10-31.md`. It supports boundary
inflow as the leading explanation without establishing flux closure or
identifying the paired mass difference as nozzle injection.
