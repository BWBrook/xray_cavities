# X-ray Cavity Production Validation

Date: 2026-07-23
Status: `failed_closed`
Decision label:
`XRAY_CAVITY_PRODUCTION_VALIDATION_FAILED_CLOSED_RECOVERY_METHOD_REFINEMENT_REQUIRED`

## Result

Goal 044 executed Patrick-agent's requested production path using two
nonuniform PLUTO-schema synthetic fixtures and the accepted real C-HI endpoint.
All 24 synthetic XRAiSE products, four real-endpoint products, and their
deterministic repeats completed. The validator then failed closed with seven of
ten predeclared gates passing.

This is a useful validation result, not a failed compute attempt. It supports
the production projector while withholding certification of the downstream
tracer-blind cavity-recovery and hybrid-energy surface.

## Observations

The following gates passed:

- fixture schema and nonuniform axes;
- physical flux conservation, worst relative error
  `1.2379950358787574e-10` against `1e-9`;
- native-axis equivalence, worst normalized L1 residual
  `8.534190750687258e-11` against `1e-9`;
- near-90-degree continuity, worst normalized L1 residual
  `1.8657644121316622e-4` against `0.05`;
- zero empty projected columns across raw, corrected, and ratio layers;
- deterministic reruns, `113/113` byte-identical files;
- complete provenance hashes.

Three gates failed:

1. **Synthetic cavity recovery.** Only `6/12` primary synthetic views returned
   the required two opposite-side X-ray components, although X-ray precision
   against projected tracer was `1.0` throughout. The fixed highest-deficit
   one-percent physical-area mask sometimes selected only the deeper lobe in
   the deliberately asymmetric fixture and split the coarse 45-degree
   axisymmetric core.
2. **Real endpoint recovery equivalence.** Direct-90 and edge-90 maps agree to
   normalized L1 `8.534190750687258e-11`, but recovery was applied on their
   different native horizontal grids. The resulting masks differed by `4.35%`
   in area and `2.36%` in geometric-depth volume, violating the predeclared
   exact-equality gate.
3. **Energy convention.** Degenerate synthetic mask fragments had zero minor
   semiaxis and therefore zero geometric-depth volume and energy. The gate
   correctly failed positivity, although its first-run observed-text summary
   overstated the number of positive rows.

## Interpretation

The map-level evidence is strong: the direct native-axis and edge-overlap
projectors conserve physical flux, agree on a common grid, remain continuous
near 90 degrees, populate every column, and reproduce byte-identically.

The synthetic recovery failure is a material method finding. The one-percent
tail is a high-purity core detector, but it is not guaranteed to recover both
lobes when their deficits are asymmetric or sparsely sampled. It would be
scientifically inappropriate to relax the threshold after seeing this result
solely to make the gate green.

The real-endpoint recovery failure is instead a validation-design defect: the
requested comparison was on a common physical grid, while the first evaluator
ran the mask method separately on two native discretizations. That comparison
must be repaired before it is interpreted as physical method disagreement.

The energy failure is downstream of the synthetic recovery geometry. It does
not demonstrate incorrect pV arithmetic, but it correctly prevents zero-volume
fragments from being accepted as valid energy products.

## Operational Evidence

PBS job `775513.kunanyi-ohpc` / `xcav_valid` ended `F` with `Exit_status=1`,
walltime `00:32:35`, and peak reported memory `1303676kb`. Stdout records all
requested XRAiSE invocations as passed before
`validation_status=fail passed_gates=7/10`. Stderr contains only the explicit
fail-closed message.

The original wrapper stopped before building its compact archive. The retrieved
validation directory, contracts, command manifest, stdout, and stderr are
preserved under:

```text
docs/science/assets/xray_cavity_production_validation_2026-07-23/failed_run/
```

The wrapper is now patched so future failed validations archive their compact
evidence before returning the nonzero validation status. Energy reporting is
also patched to count positive rows honestly and verify exact 1/2.5/4
multipliers per component. These repairs do not alter the first-run evidence.

## Recommendation

Accept Goal 044 as a failed-closed production validation. Do not rerun XRAiSE
or PLUTO. The next goal should refine the tracer-blind recovery validation on
the existing maps, compare masks on a single conservative common grid, and
predeclare an asymmetric-cavity sensitivity criterion before one small
evaluation-only replay.

Goal 042 and Goal 043 X-ray-validation retention holds remain active until the
recovery method is either green or explicitly accepted with a documented
limitation.
