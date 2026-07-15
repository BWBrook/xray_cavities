# 2026-07-13 - Three-case common-age evolution

Status: `complete_local_synthesis`.

Decision label:
`THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE`.

Goal 041 launched the full existing-output common-age analysis for C-HI, C-LO,
and G-LO at nominal `10/20/30/40/50 Myr` and `0/45/90 deg`. Exact source
surfaces were selected from HDF5 `Time`; all selected ages are within
`0.001 Myr` of nominal and all three Level 3 baselines are exact zero-time
surfaces on the shared `1014 x 960 x 960` grid.

The jobs compute new XRAiSE, Level 1/2, cavity, and full 15-protocol recovery
surfaces at 10-40 Myr; reuse the accepted hash-locked Goal 040 endpoint at
50 Myr; and compute Level 3 thermal plus kinetic change at all five ages.
Gravity remains excluded. Full arrays remain remote, compact archives are the
retrieval products, and raw deletion requires Barry approval after synthesis
acceptance.

The original jobs entered PBS and started, but all three failed within
`8-12` seconds with `Exit_status=1`. Their common first failure was
`libsz.so.2` missing when the truth extractor launched after the wrapper had
purged the HDF5 module environment. Manifest and scratch preflights had passed.

The wrapper now keeps HDF5 dependency paths active while loading Anaconda and
fails closed on unresolved `ldd` dependencies. Remote restaging, all hashes,
combined Python/HDF5 import, six-binary linkage, syntax, and new no-overwrite
targets passed. Repaired retries:

```text
C-HI  770758.kunanyi-ohpc  c_hi_ageev_r1  Q
C-LO  770759.kunanyi-ohpc  c_lo_ageev_r1  Q
G-LO  770760.kunanyi-ohpc  g_lo_ageev_r1  Q
```

Each requests one CPU, 96 GB, and 12 hours on `normal`. The PBS stop rule was
re-invoked after one verified `Q` record for all three retries. No retry
polling occurred after that gate.

No new PLUTO production, radio/PRAiSE work, >50 Myr extension, scientific-
default change, raw deletion, commit, push, or expert escalation occurred.

On 2026-07-15 Barry requested a live sanity check because no retry completion
emails had arrived. The jobs had started immediately and all finished green:

```text
C-HI  770758.kunanyi-ohpc  F  Exit_status=0  02:16:43
C-LO  770759.kunanyi-ohpc  F  Exit_status=0  02:22:12
G-LO  770760.kunanyi-ohpc  F  Exit_status=0  02:22:59
```

All three final records report `Stageout_status=1`; this remains a scheduler
caveat and may be associated with the absent notifications, but the exact
email mechanism was not proven. Stage-root archives/stdout/stderr were intact.
The three compact archives were retrieved, opened, extracted, and verified
against their internal SHA-256 manifests; all stderr files are empty. Each case
metadata surface reports `complete_case_product_pending_endpoint_merge`.

Goal 041 is therefore ready for its local endpoint merge and cross-case
synthesis. No further remote compute is required for that step.

The local merge completed on 2026-07-15. It caught a C-HI Level 1 binding bug:
the returned Goal 041 manifests used `1e44 erg/s` although the frozen design
and accepted endpoint use one-sided `1e45 erg/s`. Original retrieved products
were preserved. The synthesis corrects only derived C-HI Level 1 values and
dependent ratios, records the correction explicitly, and hardens the case
builder and PBS preflight against recurrence.

Final local status: `complete_local_synthesis`.

Decision label: `THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE`.

The merged surface contains 15 case-age truth rows, 45 observer rows, 963
hybrid energy/power rows, and 45 method-sensitivity summaries. C-HI Level 2 /
injection declines `0.513 -> 0.440`; C-LO rises `0.480 -> 0.638`; G-LO remains
near `0.46-0.51`. Level 3 / injection rises `0.722 -> 0.888`, `3.32 -> 12.46`,
and `0.871 -> 1.091` respectively. These are descriptive normalized responses,
not closed energy partitions or causal estimates.

No raw or remote intermediate deletion occurred. Lifecycle compaction remains
pending synthesis acceptance and a separate Barry-authorized deletion record.
