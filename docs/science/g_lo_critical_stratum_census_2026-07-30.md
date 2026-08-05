# G-LO critical-stratum census — 2026-07-30

Status: `complete_no_recompute_finalization`

## Why this analysis

Goal 051's stable numerical machinery is green, but its formal comparison
fails because 95.1% of pressure-method discrepancy falls within the top 1% of
represented population mass. Two histories contribute 83.4% of the weighted
discrepancy. They are two of four ordinary sampled histories representing 249
ordinary members of one 262-row stratum.

That result can be either a real localized regime or high sample leverage. The
direct resolution is to calculate all 262 histories already present in the
immutable cache.

## Method

The census reuses the exact Goal 049 feature and stratification definitions.
It requires 262 unique target rows, including the 17 original Goal 051 rows,
and gives each row weight one. It repeats the unchanged stable full-loss,
stable adiabatic, and lossless branches for both pressure treatments and both
frequencies.

A hybrid population estimate retains Goal 051 rows and weights outside the
target stratum, removes its 17 weighted target rows, and inserts all 262 census
rows with unit weights. The replacement must preserve total represented
population mass.

## Interpretation boundary

The exact census removes sampling uncertainty inside this stratum, not
uncertainty in other sampled strata, simulation assumptions, pressure
preprocessing, or transfer to observables. The 0.50 concentration threshold is
not weakened after seeing Goal 051. A distributed census-stratum pattern is
evidence consistent with localized sensitivity; the two concentration
statistics alone do not prove that this stratum causes any residual hybrid
population concentration.

No simulation, raw-history production, raytracing, new frequency, or
scientific-default change is part of this goal.

## Result

PBS `780326.kunanyi-ohpc` / `g_lo_strcen` finished with `Exit_status=2` after
`00:34:56`. The retrieved archive shows that the full 262-history census and
all 22 stable-core gates completed before a bitwise-exact Goal 051 oracle gate
stopped downstream summary generation.

Of 204 replayed branch cells, 168 are bitwise identical and 36 differ. All
differences are confined to physical IDs `196752`, `197253`, and `197269`.
The maximum absolute and relative differences are
`9.15421913206577e-50` and `9.1601327385061e-12`. Every cell satisfies the
existing project equivalence tolerance:

```text
abs(diff) <= abs(original) * 1e-10
             + 8 * max(abs(spacing(original)), abs(spacing(census)))
```

The worst cell uses `0.09160043107217158` of its tolerance.

A local no-recompute finalizer validated the preserved CSV and NPZ evidence,
row identities and order, feature values, weights, represented mass, and
oracle tolerance before generating the missing products in a fresh directory.
It did not open the immutable cache or recompute any stable branch.

The recovered top-1%-mass discrepancy fractions are:

| Scope | Fraction | Threshold |
| --- | ---: | ---: |
| 262-history census stratum | `0.07069644733314163` | `0.50` |
| Hybrid population | `0.883220701841804` | `0.50` |

The predeclared classification is:

```text
CENSUS_SUPPORTS_LOCALIZED_REGIME
```

This is evidence consistent with distributed localized sensitivity inside
the censused stratum while the hybrid population remains concentrated. It is
not proof that the stratum causes the population-level discrepancy, does not
quantify physical uncertainty, and does not authorize a production-method
default change.

Failure evidence:

```text
docs/science/assets/g_lo_critical_stratum_census_failure_2026-07-30/
```

No-recompute result:

```text
docs/science/assets/g_lo_critical_stratum_census_repair_2026-07-30/
```
