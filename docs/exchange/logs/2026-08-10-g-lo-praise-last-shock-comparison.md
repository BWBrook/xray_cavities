# G-LO last-shock PRAiSE comparison

Date: 2026-08-10
Goal: 056
Status: `complete_diagnostic_review_requested`

Patrick's review superseded the provisional Goal 055 production convention:
pinned `plutokore.radio.praise2.praise(...)` is the intended reference, subject
to a deterministic interval-aware particle comparison. Goal 056 implements
that requested gate without modifying PRAiSE2.

The comparison uses the exact Goal 051 4096-particle panel and Goal 050
comparator, the immutable G-LO history cache, and pinned `plutokore` commit
`e80252cf35ff5a06166240e2867d3d485aaf6956`. It compares PRAiSE1, PRAiSE2's
native smoothing workflow, PRAiSE2 on controlled common raw inputs, and Goal
050 at representative timesteps from each particle's latest shock onward.

Local tests passed (`13 passed`), as did wrapper syntax and diff hygiene. A
remote import preflight caught an omitted established `yt` import shim before
submission. After restaging all three existing Kunanyi compatibility shims,
the complete staged manifest and runtime import preflight passed.

PBS job `784909.kunanyi-ohpc` (`g_lo_lstcmp`) was submitted to `normal` and
verified queued at `2026-08-10 22:13:13` Hobart time. Requested resources are
one node, 16 CPUs, 96 GB, and 24 hours. Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal056_g_lo_praise_last_shock_comparison/g_lo_praise_last_shock_comparison_2026-08-10.tar.gz
```

No polling, matched radio production, PLUTO work, or scientific-default change
followed queued-state verification.

## First-attempt failure and repair

Barry reported that PBS `784909.kunanyi-ohpc` completed with `Exit_status=1`.
Retrieved compact logs show that staged hashes, the 33 GB cache hash, selection
and comparator hashes, and runtime imports all passed. The diagnostic then
failed on an invalid assumption that PRAiSE2's uniform resampler must retain
every irregular source timestep. The wrapper's attempt to archive that failure
also hit `Permission denied` because it invoked the byte-preserved archive
helper directly rather than through `bash`.

The original job/stage remains immutable failed provenance. No science result
is claimed from it. A focused repair now:

- accepts expected omitted intermediate source indices while recording the
  exact retained indices and bounding endpoint lag;
- reproduces pinned PRAiSE2's preprocessing order of uniform resampling,
  backfilling, and then optional native linear Savitzky-Golay smoothing;
- maps replay rows back to their exact source/global indices; and
- invokes the archive helper through `bash`.

Focused local tests passed (`15 passed`), including raw and native-smoothed
irregular histories compared directly with pinned PRAiSE2. The same
native-smoothed irregular-history proof passed in the staged Kunanyi runtime.
Remote staged SHA-256s matched local:

```text
600655ae0761afe0bdb8bdde89505802608c71cbecdca7d2d0e54e0a44416b66  diagnose_praise2_method_validation.py
43f8045677b3cf81ae917da8b05cc30df570c20b78b1decac7cc70788ebdca82  diagnose_praise_last_shock_comparison.py
9ba01644e774fe4d3c8185b8853dfb84e475ed0e5d90305218df5d3bef082672  g_lo_praise_last_shock_comparison.pbs
```

PBS retry `784931.kunanyi-ohpc` (`g_lo_lstcmp_r1`) was submitted under fresh
stage/analysis paths and verified queued in `normal` at `2026-08-11 10:56:35`
Hobart time. It requests one node, 16 CPUs, 96 GB, and 24 hours. The stop rule
was invoked immediately; wait for Barry's completion email before retrieval.

Separately, Stas supplied the missing gravitational-energy convention. Future
energetics post-processing should derive `Phi_0(r)` from the initial
`tabulated_cosmo_002003.csv` acceleration profile and integrate
`[m(t)-m(0)] Phi_0(r)` cellwise, reporting tracer-weighted gas and lobe terms.
That method is now defined but has not yet been computed.

## Retry failure and final repair

Barry reported PBS `784931.kunanyi-ohpc` completed with `Exit_status=2` after
`02:08:29`. The repaired PRAiSE2 path progressed through the earlier failure
points and reached the representative detailed panel. That panel failed when
its contextual Goal 050 comparator treated all frequencies as finite and
called the finite-only reconstruction with a non-finite endpoint/injection
gamma.

The failure archive was produced and retrieved successfully; its SHA-256 is
`c3ef7c511814f69e413d7ddacf8197ce999dc7597f6da82214c685cf7f752662`.
No analysis root or science decision was produced. The failure is documented
in `docs/science/g_lo_praise_last_shock_comparison_retry_failure_2026-08-11.md`.

The narrow repair now carries Goal 050's per-frequency state into the panel:
explicit cutoffs remain zero, finite states are reconstructed, and
subrelativistic/non-finite states remain unavailable. It does not weaken or
change the PRAiSE2 gates. Local focused validation passed (`16 passed`); the
same state-aware case, staged hashes, and wrapper syntax passed remotely.

PBS `784939.kunanyi-ohpc` (`g_lo_lstcmp_r2`) was submitted under fresh stage
and analysis paths and verified queued at `2026-08-11 14:32:28` Hobart time
with one node, 16 CPUs, 96 GB, and `24:00:00` walltime. The stop rule is active.
If this final retry finds another material failure, stop for method
reassessment rather than continue an incremental retry chain.

## Final completion and method reassessment

PBS `784939.kunanyi-ohpc` completed the diagnostic and archive, then returned
the predeclared science-hold exit `3`. The retained-pressure and native
numerical gates passed. The only failed gate comprised two checks of one
width-one representative history. Those checks called the full-loss branch
directly instead of using the already approved population singleton convention
where lossless equals full because no elapsed interval exists.

The immutable run remains labelled `PRAISE2_LAST_SHOCK_HOLD_FOR_REVIEW`.
Local reassessment found all `62/62` applicable direct full-loss replays exact;
48 singleton histories comprise only `0.0243%` of represented weight. The
diagnostic contract is repaired and tested locally, and no fourth remote run
was submitted.

The completed tables answer Patrick's substantive question. PRAiSE2's
difference from PRAiSE1 persists on common raw pressure: material fractions
are `17.96%` at `0.15 GHz`, `27.17%` at `1.4 GHz`, and `12.79%` for spectral
index. Native smoothing alone is material for `0.756%` of weight and `0%` for
spectral index. The difference is therefore principally recurrence,
coefficient, and cutoff behaviour rather than pressure smoothing.

The local review decision is
`PRAISE2_USABLE_METHOD_DIFFERENCE_PERSISTS_PATRICK_CONFIRMATION_REQUIRED`.
Matched history production remains held for one concise Patrick confirmation;
no further Goal 056 compute is recommended.
