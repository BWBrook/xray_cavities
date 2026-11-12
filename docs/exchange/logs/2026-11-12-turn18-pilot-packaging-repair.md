# Accounting pilot packaging repair

12 November 2026. Barry reported morning completion emails with exit error 2.
All three submitted pilots failed during pytest collection, before native
accounting began. Codex omitted a transitive test dependency from the staged
payload. The failed stage, archive and logs are preserved unchanged.

## Diagnosis and repair

| Original pilot | Job | Final state / exit | Wall time |
| --- | --- | --- | --- |
| C-LO/20 fixed box and regional mass | 878890 | F / 2 | 00:00:17 |
| G-HI/20 fixed box and regional mass | 878891 | F / 2 | 00:00:05 |
| G-LO/0--1 flux/source balance | 878892 | F / 2 | 00:00:02 |

Each log reports `ModuleNotFoundError: No module named 'run_spherical_budget_case'`.
`test_review_accounting.py` imports a fixture from
`test_spherical_budget_inputs.py`, which imports that omitted runner. The
failure reproduces from the submitted R1 bundle locally. Tests in the owning
checkout had hidden the incomplete dependency closure. No new scientific
product was produced by these jobs.

Commit **817779598bf297cb110544cf68204e01d7211e20** adds
`scripts/kunanyi/verify_accounting_stage.py` and three packaging regression
tests. The verifier checks regular-file presence and import origins in a
fresh isolated Python process, then runs the 46 accounting checks using
only packaged project modules and fixtures. Its tests cover complete copied
payloads, a missing transitive helper, and an external symlink, including
an ambient `PYTHONPATH` pointing to the owning checkout.

The exact repaired archive was freshly extracted outside the checkout:
**46 passed in 1.54 seconds**. All three packaging regressions also pass.
All 15 originally packaged source/test files and all eight native request
JSONs are byte-identical to R1. The added helper is unchanged repository
source. Scientific calculations, frozen emission configuration, native
identity/lineage gates and compatible-host pins were not altered.

Reproduce the packaging regressions with
`uv run pytest -q tests/test_accounting_stage.py`. For a separately extracted
stage, run `python -B scripts/kunanyi/verify_accounting_stage.py <stage>`
with the project's scientific Python environment; the verifier starts the
isolated child itself.

## Replacement submissions and custody

At **12:31:59 AEDT**:

| Replacement pilot | Job | Observed state |
| --- | --- | --- |
| C-LO/20 fixed box and regional mass | 879122 | Q; compatible host capacity unavailable |
| G-HI/20 fixed box and regional mass | 879123 | Q; compatible host capacity unavailable |
| G-LO/0--1 flux/source balance | 879124 | H; afterany 879122 to serialize I/O |

Each launcher includes completion/abort mail, and submission also explicitly
sets it. Fresh scheduler readback confirms `Mail_Points = ae` and Barry's
UTAS recipient for all three. Each submission has an exclusive per-job JSON
receipt in the replacement stage's `submissions/` directory. These are
accepted jobs, not completed or validated native analyses.

Replacement stage: `turn18_accounting_2026-11-12_r2`, source **8177795**.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `turn18_accounting_2026-11-12_r2.tar.gz` | 98,708 | `1f4e907bd55874eac83ba9745f0d427580e991d5714c42e44cd1dffd10c4b4ff` |
| `stage_checksums.sha256` | — | `52fedf9d9bc088db3c3692dc33c5a6127e0fd5c5a97ac7dda4ce9c85a8a35b81` |
| `turn18_repair_capture_2026-11-12_r1.tar.gz` | 11,438 | `ef80e1f26d63b325024c9d940be9dd6c28863f7a6b06b84825da1d1a9deba6a3` |
| `turn18_repair_local_verification_2026-11-12_r1.tar.gz` | 2,712 | `264df7f8ac9243268aa6bb5009b519f46b0213525ff5cf982f73b2504613b789` |

The replacement archive has 38 safe regular members. Its checksum and every
manifest member matched after upload/extraction. The capture has 21 safe
regular members: old failure logs, old/new scheduler records, submission
receipts, manifests and capture metadata. Its archive checksum and every
captured member matched after download. Raw scheduler records remain in
ignored storage; this handover omits infrastructure and recipient details.

Local custody: `private_archive/turn18_repair_2026-11-12/` contains the builder,
isolated exact-archive verification receipt and extracted remote capture;
archives are in `private_archive/incoming/`. The browser's unavoidable
Downloads copy was immediately relocated and hash-verified; no project
payload remains there.

All three archives are retained at
`nectar:/data/share/xray_cavities/turn18_repair_2026-11-12/`; fresh remote
readback matches every archive hash above. The local verification archive
preserves the R2 builder and exact isolated-test receipt. The reviewed board
snapshot was refreshed under the existing publication policy; no new board
message or collaborator email was sent.

## Resume at pilot review

Full-history requests remain staged, not submitted. On the next check, inspect
the three jobs and their logs, verify aggregate completion and product hashes,
then apply the acceptance checks in the
[original handover](2026-11-11-turn18-review-and-accounting-pilots.md).
Reconcile R100/R300 to accepted products, regional mass/energy partitions,
potential-shift identities and fixed-inset coverage before scaling up.
Do not relax native identity gates to evade queueing.

Historical in-grid source terms remain unidentifiable individually from
primitive snapshots. BND-05 remains provisional; no new energy-budget result,
detector validation or held-out emission score is reported by this repair.

Next: Codex — inspect replacement pilot completion and native products.
