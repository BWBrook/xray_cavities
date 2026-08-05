# G-LO Critical-Stratum Census No-Recompute Repair

Date: 2026-07-30

Status:

```text
complete_no_recompute_finalization
```

Decision:

```text
CENSUS_SUPPORTS_LOCALIZED_REGIME
```

## Repair

The zero-tolerance replay gate was replaced by the project numerical-
equivalence contract:

```text
abs(diff) <= abs(original) * 1e-10
             + 8 * max(abs(spacing(original)), abs(spacing(census)))
```

Exact replay remains an audit statistic. Above-tolerance replay remains a
fail-closed error.

The new finalizer consumes only the retrieved partial Goal 053 directory. It
does not open the immutable G-LO cache and does not call the stable-method
diagnostic. Before generating downstream products it validates:

- original selection/comparison hashes and exact 4096-row identity/order;
- census row count, uniqueness, feature values, and Goal 051 oracle subset;
- original and census CSV-to-NPZ branch identity;
- represented target and total population mass;
- every oracle branch cell under the rtol-plus-ULP contract;
- fresh no-overwrite output.

## Evidence

| Metric | Value |
| --- | ---: |
| Census rows | `262` |
| Oracle histories | `17` |
| Oracle branch cells | `204` |
| Non-bitwise-identical cells | `36` |
| Maximum relative difference | `9.1601327385061e-12` |
| Maximum tolerance fraction | `0.09160043107217158` |
| Census top-1% concentration | `0.07069644733314163` |
| Hybrid top-1% concentration | `0.883220701841804` |
| Predeclared threshold | `0.50` |

All 22 inherited stable-core gates pass and the cutoff table is empty.
Replacing the three non-bitwise-identical histories with the exact Goal 051
values leaves the decision unchanged to approximately 14 decimal places.

Machine-readable outputs:

```text
docs/science/assets/g_lo_critical_stratum_census_repair_2026-07-30/
```

The original scheduler evidence remains separately preserved:

```text
docs/science/assets/g_lo_critical_stratum_census_failure_2026-07-30/
```

## Validation

- `63` related diagnostic, finalizer, stable-method, pressure-method, and PBS
  wrapper tests passed.
- Both Python files compiled.
- Wrapper `bash -n` and `shellcheck` passed.
- All repair/failure JSON and CSV assets parsed with unique, width-consistent
  schemas.
- Both local SHA-256 manifests verified.
- The retrieved archive remained readable and matched its recorded SHA-256.
- `git diff --check` passed.

## Interpretation

The census shows that discrepancy is distributed within the formerly
high-leverage 262-history stratum, while the hybrid population remains
concentrated. This supports a localized-sensitivity interpretation rather than
the conclusion that Goal 051's two influential histories alone define the
regime.

The result is diagnostic for this simulation/cache. It is not causal
attribution, a physical uncertainty estimate, a publication-ready observable,
or authorization to change the production pressure method or PRAiSE2
implementation.

## Scheduler Caveat

PBS `780326.kunanyi-ohpc` remains `Exit_status=2`. This local repair does not
rewrite that fact or claim a successful scheduler completion. No replacement
PBS job was submitted.
