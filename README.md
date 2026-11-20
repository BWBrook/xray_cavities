# X-ray cavities as measures of jet energy

How faithfully do cavities in X-ray images measure the energy that radio
jets transfer to hot gas in galaxy clusters and groups?

This project tests that inference against four deterministic hydrodynamic
jet simulations. It compares the full three-dimensional fluid state with
synthetic X-ray and radio observations, separating the physical energy proxy, the measurement
of cavity geometry, and the age estimate used to infer power. The primary
enthalpy convention is **2.5pV**; **4pV** is a literature comparator. Labelled
jet power times age is the reference input. The production injector has
also been measured at all 201 saved states across the four runs.

> **Status, 21 November 2026:** active research, developed in the open. The
> results below are bounded by the [claims ledger](claims/claims.yaml);
> they are not a validated universal calibration of cavity power.

## Start here

| Reader | Starting point |
| --- | --- |
| What has been learned? | [Reviewed energy and emission results](docs/science/turn15_energy_emission_review_2026-11-11.md), followed by the [review reconciliation](docs/science/turn18_review_reconciliation_2026-11-11.md) |
| Latest accounting result? | [Full jet energy budgets, tracer leakage and the gravity test](docs/science/production_injector_histories_2026-11-21.md) |
| What is established, provisional or withdrawn? | [Claims ledger](claims/claims.yaml) and [status definitions](claims/README.md) |
| Joining or resuming the work? | [Current status](docs/exchange/current_status.md), then the [agent guide](AGENT_GUIDE.md) and [repository instructions](AGENTS.md) |
| How were the conclusions challenged? | [Reviewed correspondence snapshots](docs/correspondence/INDEX.md) |

The ledger and current status govern interpretation. Older reports and the
article draft retain historical results and may predate later qualifications.

## The four cases

PLUTO simulations cross two atmospheres with two labelled bipolar kinetic
powers. C denotes cluster, G group, and HI/LO the higher/lower power.

| Case | Atmosphere | Labelled power | Retained energy-history snapshots |
| --- | --- | ---: | --- |
| C-HI | Cluster | 2 × 10⁴⁵ erg/s | 0–50 |
| C-LO | Cluster | 2 × 10⁴³ erg/s | 0–50 |
| G-HI | Group | 2 × 10⁴⁵ erg/s | 0–47 |
| G-LO | Group | 2 × 10⁴³ erg/s | 0–50 |

The retained histories contain **201 snapshots** at approximately 1-Myr
spacing. G-HI snapshots 48–50 are excluded because of boundary contamination;
individual aperture measurements have additional geometry and coverage flags.
The [agent guide](AGENT_GUIDE.md) describes the simulation and observation
design, conventions and exclusions.

## What the reviewed evidence shows

R100 is the spherical aperture whose radius reaches the furthest current
cell moving at least 100 km/s in three dimensions. Its budget includes
every cell inside the sphere, including slower gas, and measures the
current-minus-initial stored energy in those cells.

- **The enthalpy-to-stored-energy ratio varies across cases.** At 30 Myr,
  native whole-lobe 2.5pV divided by the R100 stored-energy change is
  0.5054, 0.8053, 0.4338 and 0.6545 for C-HI, C-LO, G-HI and G-LO.
  These ratios use the declared gravitational-potential convention.
  <!-- claims: NAT-07 -->
- **The energy-accounting discrepancy merits further measurement.** R100
  storage and whole-grid storage minus a mass-scaled coarse boundary estimate
  agree within 0.002837 labelled-input units at 11 geometrically eligible
  selected case/ages. Their agreement strengthens the finding of excess
  storage but does not identify numerical delivery or the source of the
  excess. BND-05 remains provisional.
  <!-- claims: BND-05 NAT-08 -->
- **Surrounding gas partly hides the cavity deficit.** In the reviewed G-HI
  20-Myr maps, ambient brightening cancels about 37–44% of the lobe's
  brightness deficit. At side-on azimuths 45° and 90°, deficit outlines close
  to the native total volume still contain about 50–60% non-lobe material
  by volume.
  Correct recovered volume can therefore conceal incorrect gas selection.
  <!-- claims: XR-03 XR-04 -->

The [reconciliation](docs/science/turn18_review_reconciliation_2026-11-11.md)
gives the definitions, exact denominators and evidence paths. It supersedes
the earlier total ambient-energy-share headline and distinguishes a
truth-assisted background diagnostic from an observer-only detector.

## Work in progress

The [accounting pilots](docs/science/turn18_pilot_review_2026-11-14.md) all
completed successfully. Independent fixed-budget, flux and provenance checks
pass. At 20 Myr, the fixed interior stores 1.157066 and 1.074883 labelled-input
units in C-LO and G-HI; regional mass measurements demonstrate the potential
convention's effect on ambient shares. The first G-LO flux interval remains
too sensitive to time integration to locate the excess energy source.
<!-- claims: NAT-09 BND-06 -->

The [full C-LO accounting history](docs/science/turn18_clo_history_review_2026-11-16.md)
is now complete and independently audited. Enlarging R100 to the fixed box
does not remove the early shortfall: storage at 1 Myr is 0.922559 labelled-input
units. At 50 Myr the box stores 1.288860 units. The flux history cannot locate
the numerical source: outer-face reconstruction and time sampling change the
sign of the outside-nozzle balance. These remain provisional C-LO findings.
<!-- claims: NAT-10 BND-07 -->

All four fixed-box histories are complete. At 50 Myr G-LO stores 1.17814
times labelled input inside the box, which still encloses its traced lobe.
At 20 and 30 Myr the energy change outside the box agrees within 0.008%
between HI and LO in each atmosphere, despite their hundredfold power
difference. The [four-case comparison](docs/science/four_case_fixed_histories_2026-11-18.md)
shows where this resemblance breaks down at later ages.
<!-- claims: NAT-11 -->

All eight jobs in the original accounting batch have finished. Seven succeeded.
G-LO flux (879909) returned every requested snapshot. G-HI flux returned a
verified history through index 46 and failed at 47. At 30 Myr, all 36
reconstructions give a negative outside-nozzle energy balance in the two
high-power runs. The low-power runs admit both signs. Realised jet delivery
and the physical source of excess storage remain open. The
[flux comparison](docs/science/four_case_flux_histories_2026-11-18.md) gives
the numerical ranges, their interpretation and the complete batch inventory.
<!-- claims: BND-08 -->

The [G-HI endpoint addendum](docs/science/ghi_flux_endpoint_2026-11-19.md)
extends 24 of the 36 estimates through 47 Myr. All 24 give a negative
cumulative outside-nozzle balance. The other twelve require an extrapolation
that gives negative pressure on part of the negative-z boundary.
<!-- claims: BND-08 -->

On a steady jet of known power, every nozzle measurement fell below the
29–30 Myr production estimates in C-HI, G-HI and G-LO. In C-LO the centred
reconstruction can assign six times too much kinetic power to cells
straddling the jet edge. The production excess in C-LO is within the size
of error this test can generate. [Four-case calibration and figure](docs/science/nozzle_flux_calibration_2026-11-19.md)
<!-- claims: BND-08 BND-09 -->

At every saved age after startup, the sides of the grid cells that inject the
jets carried **78–82% of the excess marked mass**. The outgoing gas carried
within 0.5% of its nominal energy per gram. Over the full available histories
the net injector supplied **16.2%, 12.3%, 15.8% and 15.1% more gas energy than
label** in C-HI, C-LO, G-HI and G-LO. Through 30 Myr even the most dilute
recorded tracer remained at least 93 kpc from a domain face in every run.

After accounting for outer-boundary transport, G-HI's whole-grid energy
source was 7.8% above label by 47 Myr. The deficit outside its injector
was about 8% of labelled input. Two
ways of measuring gravitational work on that same gas agreed to within 1.03%
of the deficit's magnitude in every matched interval and method. The cause
of the remaining imbalance is open. [Four-case results, figure and replay](docs/science/production_injector_histories_2026-11-21.md)
<!-- claims: BND-08 BND-10 BND-11 BND-12 BND-13 -->

The [prospective background test](docs/science/background_refit_blind_protocol_2026-11-11.md)
is frozen and unscored. Its truth-assisted diagnostic and observer-only
comparator remain separate. Exact historical gravity-update, floor and
conversion-repair energies cannot be recovered individually from primitive
snapshots alone.

See the [current handover](docs/exchange/current_status.md) and
[pilot repair record](docs/exchange/logs/2026-11-12-turn18-pilot-packaging-repair.md)
for execution receipts, acceptance checks and remaining work.

## Reproduce and develop

This repository owns the Python analysis scripts, tests, run specifications,
compact evidence and scientific documentation. The simulation source lives
in separate UTAS AGN `pluto`, `jet-setup` and `plutokore` repositories.

The environment requires **Python 3.12** and an adjacent `plutokore` checkout:
[pyproject.toml](pyproject.toml) resolves it as an editable dependency at
`../../git/utas-agn/plutokore`, relative to this repository. A clone of this
repository alone is therefore insufficient to install the full environment.

With that dependency available, run from the repository root:

```bash
uv sync
uv run python scripts/claims/check_claims.py
uv run pytest -q tests/test_accounting_stage.py
```

The first check validates ledger structure and pinned evidence references;
the second checks accounting-package isolation and omitted-dependency failure
modes. They do not rerun the production simulations or establish physical
energy closure. Reproduction commands for individual scientific claims are
recorded in the ledger and linked reports.

`scipy<1.14` and `sphinx<7` are intentional constraints for the upstream
verification and documentation tooling. Historical machine/toolchain setup
is recorded in [the environment notes](docs/deep_server_setup.md).

## Article, brief and agent guide

Three products draw on the same claims ledger:

- The [article draft](manuscript/text/main.md), with its
  [build workflow](manuscript/README.md).
- A brief of at most two A4 pages for a broad audience; not yet drafted.
- The [agent guide](AGENT_GUIDE.md), covering evidence, conventions,
  failed methods, reproduction and open questions.

The article is a working draft; its interpretation has not yet been fully
reconciled with the latest review. Builds use the external `makedoc` engine:

```bash
make manuscript-validate
make manuscript-draft
make manuscript-check
```

Set `MAKEDOC_DIR` if that engine is installed outside the Makefile's default
location. Build targets prepare review artifacts; they do not submit or
release the paper.

## Bulk data

Raw production outputs remain on kunanyi. Large regenerable maps, arrays
and archives belong outside Git, with manifests, hashes and provenance
pointers retained here. Shared project storage is
`nectar:/data/share/xray_cavities/`; see the
[review evidence manifest](docs/science/assets/turn15_review_2026-11-11/README.md)
and [reconciliation evidence manifest](docs/science/assets/turn18_reconciliation_2026-11-11/README.md)
for the relevant packages and checksums.

Some analysis scripts support `XRAY_CAVITIES_DATA=<data-root>`; the default
is the repository root. Restore the required payloads in their documented
layout. Tests listed in [tests/bulk_data_tests.txt](tests/bulk_data_tests.txt)
skip when their bulk-data sentinel is absent; that skip is not verification
of the scientific products.

Project transfers use the ignored `private_archive/incoming/` directory,
then move to their verified canonical location. Downloads is not project
storage. Publisher papers, private correspondence and student material are
excluded from publication. Public board discussions are reviewed snapshots
under [the publication policy](docs/correspondence/publication.toml).

## Licence

Code is released under the [MIT Licence](LICENSE). Project text, figures
and data are released under [CC BY-SA 4.0](LICENSE-CONTENT). Third-party
material retains its own terms; see [THIRD_PARTY.md](THIRD_PARTY.md).
