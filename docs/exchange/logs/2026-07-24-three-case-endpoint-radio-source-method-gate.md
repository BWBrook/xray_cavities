# 2026-07-24 Three-Case Endpoint Radio Source And Method Gate

Status: `complete_source_method_gate_g_lo_method_value_gate_required`

Decision label:
`THREE_CASE_LOSS_AWARE_RADIO_BLOCKED_G_LO_METHOD_VALUE_GATE_REQUIRED`

Goal 048 audited the retained endpoint particle sources and the available
PRAiSE/raytracing implementations before launching any three-case radio
analysis.

Read-only Kunanyi inspection found:

```text
C-HI: particle outputs 4277 and 5000 only
C-LO: particle outputs 1611 and 5003 only
G-LO: continuous particle filenames 0000..5000 across initial and guarded roots
```

The existing C-HI dense caches reach only early time or `33.374 Myr`; the
longest is from the reduced-grid rehearsal, not the accepted final full-grid
lineage. The final sparse C-HI window is interface evidence, not complete
source-lifetime history.

G-LO's filename coverage is a candidate source surface. Its cross-root seam,
physical-time cadence, schemas, endpoint-ID histories, and missing-record
classification remain to be validated before it can be called a usable full
history.

The legacy staged `xraise.py` also has an ambiguous `emis` contract: its
low-level path computes a loss factor while its wrapper attaches emissivity
units. Current `plutokore` supplies candidate full-emissivity PRAiSE and
multi-frequency raytracing functions, but the actual functions have not yet
passed production numerical, disconnected-support, convergence, determinism,
or memory/restart validation.

Goal 048 therefore failed closed before product generation. It froze the
common `150 MHz`/`1.4 GHz`, `0/45/90 deg`, common-grid/beam/threshold protocol
and added deterministic local integration, convolution, and view-invariance
fixtures.

Recommendation: run a G-LO recovery/method/value-of-information gate first.
Validate the retained history and candidate implementation, use a
field-selective chunked path, and quantify full-loss versus matched
endpoint-lossless differences. Escalate new C-HI/C-LO history production only
if that gate shows material thesis value and feasible execution. Otherwise use
a clearly labelled matched lossless endpoint reference. Do not mix methods.

Validation: focused tests `3 passed`; the deterministic builder regenerated
five CSVs plus metadata; exact ledger counts/ranges/gaps, JSON/CSV schemas,
Python compilation, payload guards, stale-label scans, and
`git diff --check` passed.

No PBS job, PLUTO production, radio map, remote mutation, raw-data deletion,
commit, or push occurred.
