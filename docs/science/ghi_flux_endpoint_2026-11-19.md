# The final G-HI flux interval

At 47 Myr the traced G-HI lobe touches the simulation boundary. The
reconstructed cumulative energy balance outside the nozzle is negative
under all 24 estimates that can be evaluated there. They span −7.14% to
−2.83% of the labelled bipolar kinetic input since startup. For the last
interval alone the range is −8.24% to −6.10% of the input during that
interval. At the preceding snapshot all 36 combinations gave a negative
cumulative balance. Twelve combinations lose coverage at the endpoint.
<!-- claims: BND-08 -->

## Where the boundary reconstruction failed

The two saved layers next to the negative-z boundary both have positive
pressure. Extending the slope between their cell centres out to the face at
−250 kpc gives a negative pressure in 29,714 of 921,600 face cells
(3.22%). Pressure on this one face accounts for every invalid value.
The original face check rejects the resulting reconstruction. All native
boundary primitives pass their checks. The independent fixed-volume
calculation agrees with whole-grid storage at the endpoint to within
1.7 × 10⁻¹⁵ of cumulative labelled input.

Using the outermost saved cells, the negative-z face changes from net
inward energy transport at 46 Myr to net outward transport at 47 Myr
(−1.71 × 10⁴² to +2.17 × 10⁴² erg/s, outward positive). Summed over all
six faces, energy transport at 47 Myr is still inward (−1.08 × 10⁴³ erg/s).
The [six face measurements](assets/ghi_flux_endpoint_2026-11-19/native_outer47_face_signs.csv)
give the mass and energy fluxes separately.

## Which estimates survive

The outside-nozzle balance subtracts the nozzle-control balance from the
whole-grid balance. Each combines the change in stored energy and the
integrated outward flux, with gravitational potential zero at the centre.
The six nozzle choices combine three control-volume sizes with two
reconstructions. The ranges below span those six choices. The denominators
are 6.309 × 10⁵⁸ erg for the last interval and 2.966 × 10⁶⁰ erg for the
full history, using the actual saved times.

| Domain face and time rule | 46–47 Myr, fraction of interval input | 0–47 Myr, fraction of cumulative input |
| --- | ---: | ---: |
| Outer active cell, left rectangle | −0.08185 to −0.06285 | −0.04680 to −0.02834 |
| Outer active cell, trapezoid | −0.08094 to −0.06195 | −0.05908 to −0.04042 |
| Outer active cell, right rectangle | −0.08004 to −0.06104 | −0.07136 to −0.05249 |
| Linear to face, left rectangle | −0.08240 to −0.06340 | −0.04731 to −0.02884 |
| Linear to face, trapezoid or right rectangle | Unavailable | Unavailable |

The linear left rectangle uses the valid flux at 46 Myr and the measured
storage change through 47 Myr. The trapezoid and right rectangle need the
missing 47 Myr linear face value. The [36 combinations](assets/ghi_flux_endpoint_2026-11-19/independent_final_scenarios.csv)
retain the nozzle estimates for all rows. Empty domain and outside values
mark the twelve unavailable estimates. The resulting negative balance
describes energy accounting at the saved cadence. Determining jet delivery
and the origin of the storage excess still requires solver-step accounting.
<!-- claims: BND-08 -->

## Verification and reproduction

Original flux job 879905 produced checkpoints 0–46. First addendum 881993
exited 127 before Python started because its batch shell lacked the
`module` command. Retry 882015 used the same scientific code and inputs
with an explicit interpreter. It returned exit 0 in 00:05:11. Its separate
endpoint receipt binds the source, original signature, checkpoint hashes
and native file identities. The integrator reproduced all 103,776 scalar
fields checked in the prefix. A second calculation replayed the saved
fluxes, compared whole-grid storage against the fixed-budget job and passed
30,243 numerical checks. It did not reread the native 3-D primitive arrays.

The project archive contains `turn18_ghi_addendum_2026-11-19_r2/ghi_endpoint_review_r2.tar.gz`,
SHA-256 `473bd3189346ea0da66d2b8cbadb3f9fc7b846ece400194dd5e7d4b7ce0efada`.
Restore its members under the corresponding `private_archive/` directory.
Restore the [high-power review](../exchange/logs/2026-11-18-accounting-chain-check.md)
there under its original directory name. From the repository root, the
following commands verify the transferred endpoint and reproduce the last
interval from the checkpoints. Supply a new directory for the replay.

```bash
review=private_archive/turn18_ghi_addendum_2026-11-19_r2
prior=private_archive/turn18_high_review_2026-11-18
.venv/bin/python "$review/verify_capture.py"
.venv/bin/python scripts/science/integrate_ghi_final_flux.py \
  --partial-dir "$prior/flux_audit/G-HI_partial" \
  --checkpoint-dir "$prior/stage/results/flux_G-HI_full/flux/checkpoints" \
  --endpoint "$review/capture/result/endpoint.json" \
  --qualification "$review/capture/result/qualification.json" \
  --output-dir "$review/replay"
.venv/bin/python "$review/audit/check_endpoint.py" \
  --endpoint "$review/capture/result/endpoint.json" \
  --qualification "$review/capture/result/qualification.json" \
  --integrated-dir "$review/replay"
```
