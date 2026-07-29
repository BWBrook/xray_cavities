# Goal 048 Log: Three-Case Endpoint Radio Source And Method Gate

## 2026-07-24 Approved Start

Status: `in_progress_source_method_gate`.

Starting state:

```text
cwd: /Users/bwbrook/papers/xray_cavities
branch: main
HEAD: a77b4298e7f7cb72a5840298cedd0570825a1fa8
status: clean and synchronized with origin/main
```

Barry approved Goal 048 as the next core radio-observable goal after Goal 047
completed the three-case lifecycle compaction. The intended analysis was a
common loss-aware, ray-traced endpoint product at multiple frequencies and
views, followed by joint X-ray/truth synthesis.

Three native read-only workstreams reviewed source retention, radio-method
requirements, and existing code. The root orchestrator then refreshed the
TPAC SSH selector using Chrome/Open OnDemand and performed a read-only Kunanyi
source inventory through the repo-local helper. No PBS job was active, staged,
or submitted.

## 2026-07-24 Source And Runtime Finding

Status: `source_gate_failed_closed`.

The accepted endpoint lineages do not retain comparable full particle
histories:

```text
C-HI fresh:  regular particles.4277.dbl
C-HI final:  symlink to 4277 plus regular particles.5000.dbl
C-LO final:  particles.1611.dbl and particles.5003.dbl
G-LO initial: particles.0000.dbl through particles.1499.dbl
G-LO guarded: particles.1000.dbl through particles.5000.dbl
```

Together the two G-LO roots provide continuous `0..5000` filename coverage.
That is a candidate history surface, not yet proof of uninterrupted ID-keyed
particle histories through the `1499/1500` seam. The C-HI and C-LO accepted
endpoint lineages do not even provide continuous filename coverage.

The only dense particle HDF5 caches found under the accepted analysis
allowlist were C-HI caches reaching about `5`, `10`, and `33.374 Myr`. The
longest belongs to the `404 x 404 x 452` reduced-grid rehearsal and cannot be
spliced into the accepted final full-grid endpoint lineage. No C-HI `50 Myr`,
C-LO, or G-LO dense cache was found.

The legacy staged `xraise.py` has SHA-256
`4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5`.
Its low-level `praise_aio` computes a dimensionless loss term, while its
wrapper attaches emissivity units. Existing callers consequently disagree on
whether `emis` is an emissivity or a multiplicative loss factor. That legacy
surface is not accepted for the new product.

The current local `plutokore` source at commit
`e80252cf35ff5a06166240e2867d3d485aaf6956` contains candidate
full-emissivity PRAiSE and multi-frequency particle-raytracing functions.
Source review makes it a candidate implementation surface, not a validated
production method. It requires tests through the actual PRAiSE and raytracing
functions, including disconnected-support, unit, convergence, determinism,
and memory/restart checks. It does not remove the missing-history blocker.

Observation: the source gate fails for a common full-loss analysis.

Inference: the missing C-HI/C-LO post-injection histories cannot be recovered
from endpoint particle files or the sparse late C-HI window. Reconstructing
them requires new particle-enabled production runs unless an independently
validated recovery source is supplied.

Decision: do not submit a radio-product PBS job and do not mix methods.

## 2026-07-24 Independent Scientific Audit And Repair

Status: `complete_source_method_gate_g_lo_method_value_gate_required`.

An independent methodological review accepted the central fail-closed
C-HI/C-LO source-history conclusion but identified two material overstatements:

1. G-LO has continuous retained filenames, not yet a demonstrated usable
   ID/time/schema history; and
2. current `plutokore` is a source-reviewed candidate, not an end-to-end
   validated production path.

The decision sequence was repaired accordingly. The immediate next step is a
G-LO recovery/method/value-of-information gate using retained data. It must
validate the cross-root seam, actual production functions, chunked feasibility,
and the effect of full losses relative to the matched endpoint-lossless
reference. Only a material effect plus a viable workflow should trigger
Stas/Patrick review of new C-HI/C-LO production.

The intended estimands are explicitly conditional contrasts at nominal
`50 Myr`: `C-HI - C-LO` for jet power in the cluster setup and
`G-LO - C-LO` for environment at low power. The `0/45/90 deg` views are
deterministic projections of one realization, not independent replicates.
Loss-aware and endpoint-lossless products are different estimands, and no
population-level claim is supported.

No radio-product or production job was submitted.

## 2026-07-24 Final Validation

Status: `complete_source_method_gate_g_lo_method_value_gate_required`.

Independent root verification after the material audit repair:

```text
uv run pytest tests/test_three_case_radio_source_method_gate.py -q
3 passed in 0.15s

uv run python scripts/science/build_three_case_radio_source_method_gate.py
passed

uv run python -m py_compile \
  scripts/science/build_three_case_radio_source_method_gate.py \
  tests/test_three_case_radio_source_method_gate.py
passed

git diff --check
passed
```

All five CSV assets parsed with unique headers and non-empty rows:

```text
decision_matrix.csv: 4 rows
method_acceptance_gate.csv: 13 rows
runtime_semantics_audit.csv: 6 rows
source_inventory.csv: 3 rows
source_ledger_extract.csv: 5 rows
```

The exact ledger-derived source assertions passed, including C-HI fresh
`1 x 4277`, C-HI prod64 `4277` symlink plus regular `5000`, C-LO regular
`1611/5003`, G-LO production `0..1499`, and G-LO guarded `1000..5000`.
The repaired gate marks G-LO history `pending/false`, both current
`plutokore` function gates `pending/false`, and the legacy XRAiSE semantics
`rejected_not_blocking`.

Unresolved-marker, stale-label, large-file, HDF5, PLUTO `data.*`, and particle-
payload scans were clean. The evidence bundle is compact.

Final boundary: no PBS submission, PLUTO run, radio product, remote mutation,
raw-data deletion, commit, or push occurred.
