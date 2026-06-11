# Sparse PRAiSE-Compatible Loss Interface

Date: 2026-06-11

## Summary

This note records the local interface added between the final sparse-particle
radio bridge and a future PRAiSE-compatible per-particle loss product.

The interface keeps the existing June 2026 pressure-history proxy path intact
while adding an optional external loss-table path keyed by selected particle
ID. It is a local implementation and validation contract only. It does not
claim that a final PRAiSE radio product has been generated.

## Connection To The June Sparse Bridge

The June final sparse radio bridge used selected `C-HI` sparse-window particle
rows, computed lossless 150 MHz synchrotron emissivity at the endpoint, and
multiplied by:

```text
clip(final pressure / maximum positive pressure across sparse window, 0, 1)
```

That pressure-history value remains the default loss model and is still labelled
as `pressure_history_proxy` in metadata. Its map products retain the existing
proxy filenames, including:

- `radio_150mhz_sparse_loss_proxy_mjy_sr.tsv`
- `radio_sparse_mean_loss_proxy.tsv`

## External Loss Table Contract

The bridge now accepts an optional local table:

```bash
--loss-table path/to/loss_table.csv
```

Default columns are:

| Column | Meaning |
| --- | --- |
| `id` | selected PLUTO particle ID |
| `loss_factor` | finite non-negative PRAiSE-compatible per-particle factor |

CSV is the default; `.tsv` and `.tab` files are read as tab-delimited tables.
Column names can be changed with `--loss-id-column` and
`--loss-factor-column`.

The external path is deliberately ID-keyed. The table row order is ignored, and
extra non-selected particle IDs are allowed. The bridge fails fast if a selected
particle ID is missing, duplicated, non-integer, non-finite, or has a negative
loss factor.

External-loss outputs are labelled separately:

- loss model metadata key: `external_praise_compatible`
- loss map: `radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv`
- mean loss map: `radio_sparse_mean_external_praise_loss.tsv`
- particle-row loss column: `loss_factor`

Metadata includes the table path, delimiter, ID column, loss-factor column,
matched selected-ID count, extra-ID count, and a science-status warning that
the product is an interface product rather than a final PRAiSE science map.

## Connection To The May PRAiSE Smoke Path

The May 2026 particle-loss and particle-radio smokes proved that the supplied
XRAiSE/PRAiSE machinery could ingest processed `C-HI` particle history and
produce finite particle-level loss/emissivity factors at a small 5 Myr target.
Those smoke products were runtime gates on `kunanyi`, not the final 50 Myr
sparse endpoint.

This local interface defines the table shape that a future remote PRAiSE sparse
run can feed back into the June final sparse bridge. The next remote/PRAiSE
goal should generate the real selected-ID loss table, verify deterministic
PRAiSE behavior, then run the bridge with `--loss-table` and compare the output
metadata and lobe summaries against the pressure-history proxy path.

## Remaining Caveats

- The external table path has been tested with deterministic local fixtures,
  not with a newly generated production PRAiSE loss table.
- The luminosity scale remains tied to the bridge volume-assignment convention
  supplied at runtime.
- The final observable comparison page and final grid/tracer volume coupling
  are still future work.
