# Turn-15 reviewed compact evidence

Reviewed 11 November 2026. Scientific interpretation and limits are in
[the review note](../../turn15_energy_emission_review_2026-11-11.md).
`verification_summary.json` gives the bounded verification result;
`review_manifest.json` binds the public files, rendering source and archived
review bundles. CSV bytes are preserved by the directory's Git attributes.

## Contents and definitions

- `budgets/`: four complete compact histories from the existing spherical
  summarizer. C-HI, C-LO and G-LO cover 0--50; G-HI covers retained 0--47.
- `energy/`: independently reconstructed native proxies, selected-age
  components, geometry/flag summaries and arithmetic verdict. Bulk scalar
  check traces remain in the archive.
- `emission/`: original native filling and deficit-attribution tables plus
  independent summaries, projection checks, correction/velocity sensitivities
  and the retained first-pass histogram flags with their roundoff bounds.
  The two public audit-summary copies omit the local input-directory path;
  original receipts remain in the archive.
- `figures/`: reviewed plots and SHA-256 render receipt. The C-LO component
  figure is from the existing spherical summarizer; the other two figures
  use `scripts/science/render_turn15_review.py`.

The figures use bipolar totals. Native filling pools W+ and W- numerators
and denominators, rather than taking a union or averaging their fractions.
Brightness and deficit integrate the full sightline through the observer
mask. Native lobe cells are all cells with tr1 > 1e-3 at full cell weight.
Viewing angles are side-on azimuths, not jet inclinations. Energy ratios
use labelled bipolar power times actual age, not measured realised delivery.
Current pV is absolute; storage is a current-minus-initial Eulerian change.

## Bulk evidence and restoration

The following bundles are retained at
`nectar:/data/share/xray_cavities/turn15_review_2026-11-11/`.
All three SHA-256 values were freshly read back there after transfer:

| Bundle | Bytes | SHA-256 |
| --- | ---: | --- |
| `turn15_review_compact_2026-11-11_r1.tar.gz` | 31468464 | `f09ab4bee43be9835e5ca8dacf1b5a7b9b820ca28a4e6d12cc25cf408cce182c` |
| `turn15_review_maps_2026-11-11_r1.tar` | 645160960 | `e75e5f0fedd0cc8f21126193ae802799f750fde1bbbb565c988097c9b6f9f325` |
| `turn15_review_tools_2026-11-11_r1.tar.gz` | 3373977 | `d619bc49412ede7ed4065dce93e464ec6f6696e5b8ee1139573adae7013fdae4` |

Use a fresh project checkout/restoration directory. Verify each bundle against
these hashes and inspect its member paths before extracting. Extract compact
and maps into `private_archive/turn15_review_2026-11-11/inputs/`; they merge
without replacing members. Extract tools at the repository root: its members
already have repository-relative `private_archive/` prefixes. Do not overwrite
an existing review. The tools bundle includes frozen stage contexts, review
scripts, reports, original receipts, detailed check traces and parent
summaries, with a member manifest. Raw native HDF5/restart fields are absent.
Inputs and bulk evidence are ignored by Git and may contain private access
provenance; they are not public manuscript supplements.

The independent stage source is
`46ac912cebc59713793e5981a7651a5e188e6bcc`; both G-HI stages use
`c5b438d59ec63a8de3365e2691ab54bab3d56372`. Their exact staged scientific
source blobs and saved native identities are checked by the provenance
verifier. The common native-integration sources are identical across these
two commits. The review used the existing Python 3.12 project environment
(NumPy 2.2.6 and SciPy 1.13.1 for the independent emission check).

From the repository root, after restoration:

```bash
.venv/bin/python private_archive/turn15_review_2026-11-11/product_audit/verify_products.py
.venv/bin/python private_archive/turn15_review_2026-11-11/energy_review/review_compact_budgets.py \
  --inputs private_archive/turn15_review_2026-11-11/inputs/stages \
  --output private_archive/turn15_review_2026-11-11/energy_review/rerun
.venv/bin/python private_archive/turn15_review_2026-11-11/emission_review/audit_emission.py \
  private_archive/turn15_review_2026-11-11/inputs/stages/turn15_ghi_first20_r3/results_emission/G-HI_0020
.venv/bin/python private_archive/turn15_review_2026-11-11/emission_review/qualify_histogram_roundoff.py
.venv/bin/python private_archive/turn15_review_2026-11-11/emission_review/summarize_tables.py \
  private_archive/turn15_review_2026-11-11/inputs/stages/turn15_ghi_first20_r3/results_emission/G-HI_0020
```

The provenance and emission commands write reports alongside their scripts;
run them in the fresh restoration, preserving the archived original reports.
The histogram qualifier compares the retained first-pass flags with the
final checks. Its numerical bound does not change producer masks or gates.
Load maps one view at a time on memory-limited hosts.

To reproduce the combined figures from just the committed compact tables:

```bash
MPLCONFIGDIR=/private/tmp/xray_review_mpl .venv/bin/python scripts/science/render_turn15_review.py \
  --budgets docs/science/assets/turn15_review_2026-11-11/budgets \
  --filling docs/science/assets/turn15_review_2026-11-11/emission/filling.csv \
  --attribution docs/science/assets/turn15_review_2026-11-11/emission/deficit_attribution.csv \
  --output-dir <new figure directory>
```

PDF metadata can vary on rerender; compare plotted values and input/source
pins rather than expecting a new PDF's byte hash to match the saved product.
This reproduces compact-product arithmetic and rendering, not the native
field integrations, realised input, aperture transport or a causal no-jet
comparison. Observer comparators remain diagnostic.
