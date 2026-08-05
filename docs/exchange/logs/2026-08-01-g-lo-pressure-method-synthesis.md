# Exchange log - Goal 054 G-LO pressure-method synthesis

Date: 2026-08-01
Status: `complete_local_synthesis`

Goal 054 combined the preserved Goal 051 unequal-probability comparison and
Goal 053 exact 262-history census locally. No cache read, PRAiSE calculation,
remote command, or PBS job was required.

The census-replaced hybrid preserves total represented population mass while
reducing weighted pressure-method discrepancy by `58.4531%`. Full-loss
aggregate shifts fall from about `4.4-4.5%` to `1.9%`, within the established
`0.10 dex` aggregate gate.

The exact target stratum is only `0.1326%` of population mass but contributes
`60.0462%` of hybrid discrepancy. Its internal top-1% concentration is only
`0.0706964`, showing that the signal is distributed across a rare history
regime rather than controlled by Goal 051's two influential sample rows.

All 99 uncensused strata were zeroed individually while retaining their
population rows. The leading uncensused stratum contributes `18.3132%` and is
the most decision-favourable single removal, but setting its entire
discrepancy to zero still leaves the global top-1% concentration at `0.860074`,
above the `0.50` gate. Only zeroing both leading strata clears the gate. These
are influence diagnostics, not alternative estimates.

Decision:

```text
LOCALIZED_REGIME_SYNTHESIZED_NO_FURTHER_CENSUS
```

No further targeted census is decision-relevant now. The next project step is
a local pressure-method interpretation and production-default review. This
synthesis does not itself authorize a default change or PRAiSE2 promotion.
