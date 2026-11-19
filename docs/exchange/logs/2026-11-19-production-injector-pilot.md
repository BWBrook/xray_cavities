# Production injector pilot and full-history submission, 19 November 2026

At 23:37 AEDT the four-case pilot had finished with exit 0 and G-HI had saved 22 of its 48 central cutouts, including four reused pilot epochs. The three remaining cases and the final comparison were waiting on their dependencies. The project uses its existing 201 outputs across four simulations. PBS confirmed end and abort notifications to the configured address on all six replacement and comparison jobs. [Scientific result and replay](../../science/production_injector_pilot_2026-11-19.md)

| PBS job | Work | State at 23:37 AEDT |
| ---: | --- | --- |
| 882245 | Four-case pilot, indices 19, 20, 29 and 30 | Finished, exit 0 |
| 882246 | G-HI, 48 native outputs | Running |
| 882247 | C-LO, 51 native outputs | Waiting for G-HI |
| 882248 | C-HI, 51 native outputs | Waiting for C-LO |
| 882249 | G-LO, 51 native outputs | Waiting for C-HI |
| 882251 | Combined tracer and gravity comparisons | Waiting for all four histories |

An earlier pilot, 882240, captured all 16 requested patches and then exited 1 in the summary reader. Two unavailable G-HI endpoint estimates were represented by empty fields in the published whole-grid energy table. A local replay also found that three tracer reference intervals end at 30 Myr. Indexing the reference by endpoint alone selected 20–30 Myr for a 29–30 Myr comparison. The corrected reader preserves the two endpoint gaps and joins tracer observations on case, start and end. Regression checks exercise the full archived tables. PBS cancelled the four original dependents, 882241–882244, before they ran.

The successful pilot reused all 16 cutouts. Their hashes match the original captures, their requests and the source identities. A separate local replay of the successful PBS products checked every numeric field across 192 snapshot and 96 interval rows. The interval tables were byte-identical. The largest scaled difference in the snapshot table was 2.12 × 10⁻²². A separate implementation using the retained PLUTO C source checked all 68,736 individual interface measurements. [PBS and local comparison](../../science/assets/production_injector_pilot_2026-11-19/scheduler_pilot_replay.json) · [Independent C comparison](../../science/assets/production_injector_pilot_2026-11-19/public_comparison_receipt.json)

The private shared project archive holds the following files under `turn21_injector_2026-11-19/`. Each source-cutout receipt includes its historical native digest and capture identity.

| Artifact | SHA-256 |
| --- | --- |
| Original 16 cutouts, `pilot_native_882240.tar.gz` | `a6a5b211198041fa7067fcaa86e852853392cd99b9cb6717ec1c0164036bb553` |
| Corrected analysis bundle, `injector_native_stage_52da1d7509a6.tar.gz` | `5aaf5041cfde6aaeb85bcd656f714b5edcf8d24ea76a5417d8da88aec5e1b5eb` |
| Completed pilot and receipts, `injector_pilot_882245.tar.gz` | `d3e4ccefb8cdcb16d2da63be5ff8d161c26d993ff12089796fcdee403bf509c3` |
| Independent C comparison, `native_pilot_c_review_882245.tar.gz` | `ef1461c92cee8b0d34f1c9da03f4d298beb03c5e36748dc9dd823053e9c0068b` |
| Comparison job, `injector_join_6d2436740cae.tar.gz` | `b8ce29e1e592767c8a8ce15d98fa63125946ea3717c55e86eacb9305532bdb41` |

To reproduce the native reduction, extract the corrected analysis bundle into a fresh working directory and the completed pilot into a separate directory. From the analysis directory run the commands below with a Python environment containing NumPy and h5py. Set `PILOT` to the extracted pilot directory, `REPO` to the repository and `OUT` to a fresh output directory. The second command reproduces the pilot's 16 sphere inventories and 192 matched potential-work comparisons.

```sh
python scripts/science/reduce_injector_patches.py requests "$PILOT/results" tagged_mass_intervals.csv "$OUT" --domain-balances domain_interval_energy.csv
PYTHONPATH=scripts/science python "$REPO/scripts/science/compare_injector_gravity.py" requests "$PILOT/results" "$OUT" "$OUT/gravity"
```

Each full-history job reads the central stencils and then scans the same outputs for tracer throughout the grid and within 20 kpc of its six faces. It records the signed transport and the inward- and outward-motion contributions to gravitational work. Job 882251 checks coverage and hashes before it combines the 201 epochs and 197 adjacent intervals. Its expected outputs include 591 signed tracer-transport rows, 4,720 matched gravity comparisons outside the actual injector, and 7,080 comparisons for the older rectangular control boxes. On success it writes `verified_exports/production_injector_201.tar.gz` and its digest receipt. Check each history's terminal exit and the combined receipt before updating the claims about unthresholded tracer leakage or direct gravitational work.
