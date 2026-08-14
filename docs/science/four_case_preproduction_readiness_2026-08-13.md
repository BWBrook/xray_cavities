# Four-case pre-production readiness

Date: 2026-08-13
Status: `submitted_waiting_remote_pilots`
Decision: `FOUR_CASE_CONTRACT_READY_QUOTA_AND_PILOT_GATES_PENDING`

## Purpose

Prepare the next full-history production tranche without spending the quota
increase before it exists. This package resolves four immediate questions:

1. what must be run for the matched `C-HI/C-LO/G-LO/G-HI` design;
2. how much uncompressed storage that design requires;
3. whether lossless HDF5 compression can reduce that requirement without
   changing a value or breaking the existing analysis path; and
4. whether Patrick's PRAiSE2 equation (3) coefficient correction materially
   changes the retained `G-LO` radio evidence.

## PRAiSE2 coefficient

The corrected implementation in the `plutokore` working tree uses

```text
4 sigma_T / (3 m_e c)
```

for the radiative-loss coefficient. The pinned Goal 056 source is retained as
an immutable comparator rather than rewritten. Local tests independently
derive the coefficient from physical constants and show that the old value is
approximately `0.75` of the corrected value. The lossless branch remains an
exact regression control.

PBS `785271.kunanyi-ohpc` (`g_lo_c1cmp`) is running a controlled comparison on
the immutable 4096-particle Goal 056 panel. It changes only the PRAiSE2 source
module and compares weighted emissivity, cutoff/non-finite states,
representative Lorentz histories, endpoint maps, and five-frequency spectra at
`10/20/30/40/50 Myr`. No corrected radio production is claimed until that job
finishes green.

## Reversible HDF5 compression

The pilot compressor streams datasets in bounded chunks. Numeric field arrays
use ZFP reversible mode; coordinate arrays use gzip with shuffle. It copies
group, root, and dataset attributes, then validates inventories, attributes,
dtypes, shapes, and values bit-for-bit. A successful compressed float file
must also complete the existing zero-degree XRAiSE analysis.

PBS `785272.kunanyi-ohpc` (`h5_revpil`) is running against one representative
`44.89 GB` float output and one `67.32 GB` double checkpoint. It writes new
files under a fresh analysis root. It neither replaces nor deletes the source
files. Any later deletion requires separate lifecycle authorization after the
pilot ratio, runtime, bitwise gates, and analysis-readability gate are green.

A post-submission local review hardened future use in two ways: non-floating
numeric arrays now use gzip rather than ZFP, and the wrapper exports the
installed plugin directory through `HDF5_PLUGIN_PATH` for fresh analysis
processes. PBS `785272` remains immutable at its submitted source hashes. If it
fails only at the final fresh-process readability check, retain its compression
reports and use a small no-recompression readability finalizer rather than
repeating the expensive copy.

## Matched production contract

The recommended production order after quota approval is:

1. rerun `C-HI` with full particle history;
2. rerun `C-LO` with full particle history;
3. run new `G-HI` with the same output contract; and
4. rerun `G-LO` only if later analysis exposes a specific missing surface.

All new runs use matched output cadence: float HDF5 every `1 Myr`, double HDF5
every `5 Myr`, and particle histories every `0.01 Myr`, including initial and
endpoint surfaces. The observed representative file sizes give a conservative
uncompressed estimate of `2.819 TiB` per case and `11.277 TiB` for four cases.
This supports a `16 TiB` minimum allocation and `20 TiB` preferred allocation,
leaving headroom for restart overlap, analysis products, failed attempts, and
temporary compression copies. The live compression pilot will refine, not
replace, this conservative request basis.

## G-LO analysis skeleton

The existing `G-LO` evidence is sufficient to begin staged snapshot analysis
at `0/10/20/30/40/50 Myr`:

1. verify source truth and initial atmosphere;
2. compute thermal, kinetic, gravitational, closure, shock-speed, and Mach
   surfaces using Stas's potential convention;
3. generate accepted X-ray/cavity products at `0/45/90 deg`;
4. add corrected-PRAiSE2 lossless/full-loss radio and spectral-age products
   after the coefficient gate; and
5. synthesize inferred jet powers against the known bipolar input.

This skeleton is a reusable output contract, not a second general ledger or a
large framework. Each stage has a scientific stop condition in
`g_lo_analysis_stage_contract.csv`.

## Current decision

- The four-case design and retention contract are ready.
- The quota increase remains a hard hold on new `C-HI`, `C-LO`, and `G-HI`
  production submissions.
- Existing `G-LO` analysis may proceed without a default rerun.
- Corrected PRAiSE2 radio production waits for PBS `785271`.
- Compression-based storage forecasts and any source deletion wait for PBS
  `785272` and a separate lifecycle decision.

## Assets

Machine-readable contracts are under
`docs/science/assets/four_case_preproduction_readiness_2026-08-13/`:

- `four_case_production_contract.csv`
- `uncompressed_storage_forecast.csv`
- `retention_and_compression_contract.csv`
- `g_lo_snapshot_manifest.csv`
- `g_lo_analysis_stage_contract.csv`
- `four_case_preproduction_readiness_metadata.json`

## Discussion

Expected and green locally. The work has reached the useful 80/20 stopping
point: the scientific and storage contracts are explicit, the two material
unknowns are executing as small remote pilots, and further local polishing
would not change the production decision. Remote results remain pending.
