# X-ray cavities as measures of jet energy

How faithfully do cavities in X-ray images measure the energy that radio
jets transfer to hot gas in galaxy clusters and groups?

This project tests that inference against four deterministic hydrodynamic
jet simulations. It compares the full three-dimensional fluid state with
synthetic X-ray and radio observations, separating the physical energy proxy, the measurement
of cavity geometry, and the age estimate used to infer power. The primary
enthalpy convention is **2.5pV**; **4pV** is a literature comparator. Labelled
jet power times age is the reference input, while actual numerical delivery
remains under investigation.

> **Status, 13 November 2026:** active research, developed in the open. The
> results below are bounded by the [claims ledger](claims/claims.yaml);
> they are not a validated universal calibration of cavity power.

## Start here

| Reader | Starting point |
| --- | --- |
| What has been learned? | [Reviewed energy and emission results](docs/science/turn15_energy_emission_review_2026-11-11.md), followed by the [review reconciliation](docs/science/turn18_review_reconciliation_2026-11-11.md) |
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

Regional mass and fixed 50-kpc-inset energy budgets, together with extended
flux/source accounting, are implemented. Replacement pilots **879122–879124**
were submitted after an omitted test dependency caused the original pilots
to fail before analysis. The repaired archive passed all 46 accounting
checks in isolation. The last scheduler check, **12 November at 12:31:59
AEDT**, showed two queued pilots and a third held behind the first; completion
and abort email settings were verified. No replacement native result has
yet been verified here. Full histories await pilot acceptance.

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
