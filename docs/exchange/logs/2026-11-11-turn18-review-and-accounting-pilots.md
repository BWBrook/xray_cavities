# Turn 18 review reconciliation and existing-output accounting pilots

11--12 November 2026. Barry forwarded Claude's closing review and board message
3244 for action. This tranche reconciles the inference, implements the
requested accounting and freezes a prospective refit diagnostic. It launches
no PLUTO simulation, promotes no detector and measures no new native result.

## Scientific reconciliation

Evidence and independent wording review: **632de73/06f9a2d**,
[reconciliation note](../../science/turn18_review_reconciliation_2026-11-11.md),
[compact evidence](../../science/assets/turn18_reconciliation_2026-11-11/README.md).

- Preserve BND-05 as provisional. The exact agreement is with the
  production-mass-scaled boundary estimate at 11 complete, 40-kpc-inset-
  contained selected case/ages; maximum discrepancy 0.002837 labelled-input
  units. Unscaled G-LO differs by up to 0.01390; HI/40 geometry is ineligible.
  Shared production/potential conventions remain. No unconditional
  delivered-energy rescaling or C-LO delivered-energy floor is measured.
- Restore 2.5pV as primary. At 30 Myr its R100-storage ratios are
  0.5054/0.8053/0.4338/0.6545. Retire the total ambient-share headline until
  regional mass accompanies it; use thermal-plus-kinetic shares explicitly.
- Ambient brightening cancels 37--44% of the lobe deficit, equivalent to
  39--84% of net observed deficit. The 45/90-degree 5% outlines contain
  about 50--60% non-lobe material despite near-native recovered volume.
- The favorable ambient-replaced refit is truth-assisted. The observer-only
  comparator remains separate. Prediction scores and failed early C-LO
  prediction are preserved; omitted signed energy has not been measured.

The ledger, guide and relevant answer-key expectations are reconciled to
these definitions. Historical guide-evaluation runs/scores are unchanged.
The reviewed board snapshot was refreshed through 3244 under the existing
publication policy; no new board message or collaborator email was sent.

## Accounting implementation and submitted pilots

Code commit **06d233f206c0a26ebfdd9a5cc75b3b522f523584**:

- `extract_fixed_box_energy_budget.py`: all/C/A initial/current/delta mass,
  component storage in whole grid, exact full-cell 50-kpc inset/exterior and
  R100/R300; explicit potential-shift identity, extents/contact/omitted
  disturbance. New 50-kpc geometry is computed, not copied from old flags.
- `summarize_q031_source_accounting.py`: whole-grid minus nozzle inferred
  source, retaining mass, storage and transport for all reconstruction,
  quadrature and padding variants. The exterior term remains unresolved;
  historical floor/repair/gravity-update energy is not identifiable from
  primitive snapshots alone.
- `run_review_accounting.py`: immutable requests bind exact prior completed
  input receipts and fresh native-case contracts, source stability and G-HI
  inherited lineage; no overwrites or G-HI 48--50. Independent review fixed
  a missing prior-completion schema/status/path/size binding before staging.

The immutable stage is `turn18_accounting_2026-11-11_r1`. Archive bytes 96,297,
SHA-256 `75e565371fbd7a64a7095c83041ee3346a3cfa8adbe5cb988cb28bb6bd43c78d`;
36 regular safe members. Stage manifest SHA-256
`ab33346fe43abaebe0c253b3dba80b7feefec3f3153f2930ed705e6dd4bcfe9c`.
Both archive and every staged member matched after transfer/extraction.
The exact submitted stage is also verified on Nectar.

| Pilot | PBS job | State at 23:51:51 AEDT |
| --- | --- | --- |
| C-LO/20 mass/inset/R100/R300 | 878890 | Q; insufficient compatible host capacity |
| G-HI/20 mass/inset/R100/R300 | 878891 | Q; insufficient compatible host capacity |
| G-LO/0--1 extended flux | 878892 | H; afterany 878890 for I/O serialization |

Submissions are recorded in the remote stage's `submissions/`; output paths
are its per-pilot `.out` files and `results/`. Original compatible execution
hosts are pinned because the existing saved-receipt/lineage validator uses
strict device identities. That gate is unchanged. Do not remove it to evade
the queue. Pilot mail is disabled (`Mail_Points = n`); no completion email is
promised. No new native fields were read during this turn.

Full fixed and flux requests/launchers for all four retained case histories
are staged, **not submitted**. After pilot completion, verify aggregate and
product hashes, compare R100/R300 component energies to the accepted old
products, check mass/partition/potential-shift identities and inspect the
operational coverage diagnostics. Then size/submit the full serial I/O chain
within the already authorised existing-output scope. Do not equate execution
completion with physical closure or production-boundary qualification.

## Frozen emission programme and custody

Freeze commit **c352554ce3852a8312953762a33dc80a5ff4a838** preceded new
production-field reads.

Specification checksum (SHA-256):
`aaef89201ec5e4ab7fd792b754a66b8463e9ed71756ad33e55d22f84bf9844b8`.
See [protocol](../../science/background_refit_blind_protocol_2026-11-11.md).

Producer/assembler commit **f1218f1f233f593d608ab446438ba03a145363bc** adds
source-bound generic case/age map production and exact cohort assembly.
The unchanged scientific integration kernel uses empty discarded observer
placeholders; tests show they cannot alter brightness/path fields. Separate
truth custody was corrected before use: detector inputs exclude tracer/path
truth, and the assembler binds both map and truth hashes to producer files.

The frozen cohort has 22 producer snapshots, 66 map units and 66 separate
truth units (54 science views plus 12 initial nulls), all three azimuths and
both hemispheres. G-HI/20 development is excluded. Initial-null targets are
explicitly empty, not a claim of zero nozzle tracer. Historical exposure is
declared; no held-out refit maps or metrics were inspected. The generic
producer is tested but not staged/submitted; the cohort remains unscored.

After accounting pilots are inspected, stage a source-bound producer pilot
on the existing initial-null reference, then the declared cohort. Audit the
complete producer inventory with `assemble_blind_emission_cohort.py`, seal
prediction hashes before releasing the separate scoring-truth manifest, and
retain every failed side/null/coverage flag. No oracle diagnostic can be
promoted as an observer-only detector. A new observational contamination
estimator is a separate scientific proposal, not part of this frozen test.

## Verification, archive and roles

**71 focused tests pass together**: 10 fixed-box, 21 request-runner,
15 source-balance, five frozen evaluator, eight emission adapter and
12 cohort assembler tests. The source summary also accepts the actual flux
producer's synthetic end-to-end output. These are synthetic/code checks,
not new native measurements or held-out generalization results. Claims and
public evidence hashes pass their checks. Staged text and direct asset scans
pass; scanner false positives on source-CSV and protocol checksums were
verified against the actual files, and their presentation corrected without
changing either pin.

The audit bundle and exact pilot-stage bundle have fresh verified readback
at `nectar:/data/share/xray_cavities/turn18_reconciliation_2026-11-11/`.
Hashes and restoration notes are in the committed compact-evidence README.
All transfers use ignored incoming storage; Downloads was not used.

Parent and independent workers used Codex GPT-6.1 Sol. The reconciliation
reviewer reconstructed residuals/denominators and checked final wording;
the native reviewer implemented mass accounting and independently checked
the request runner and emission adapter; the emission worker froze the test
and implemented the producer/assembler. The parent integrated, checked key
numbers/definitions, ran combined tests and verified live submissions.

Next: Codex — inspect completed accounting pilots before full reduction;
keep the frozen emission cohort unscored until its custody sequence is met.
