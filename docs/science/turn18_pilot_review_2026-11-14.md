# Accounting pilots: fixed-box excess, mass accounting and startup flux ambiguity

14 November 2026, Codex (GPT-6), with independent Codex flux and provenance
reviews. All three replacement pilots completed with exit status 0.
The source-bound measurements and independent compact checks pass acceptance
for the existing-output full histories. Scientific energy closure and source
localisation remain open. No held-out emission result is reported.

## What completed and what was checked

| Pilot | Job | Wall time | Selection |
| --- | --- | --- | --- |
| C-LO fixed box and regional mass | 879122 | 00:08:15 | index 20 |
| G-HI fixed box and regional mass | 879123 | 00:10:02 | index 20 |
| G-LO flux/source accounting | 879124 | 00:08:12 | indices 0–1 |

Each job passed all 46 packaged accounting tests before analysis. All twelve
completion products, the 41-file capture, exact request/source hashes, prior
completed input receipts, native contracts and G-HI lineage reconcile.
The independent provenance audit passes 1,254 checks. The fixed-product audit
passes 460 arithmetic, partition, gauge and prior-product comparisons; a
separate flux audit passes 2,500 scalar checks reconstructed from lower-level
face-flux and storage CSVs without importing the production summary function.

These checks independently reproduce compact arithmetic and reconcile source
and receipt identity. They do not independently repeat the native field
integrals, rehash the bulk HDF5 payloads, attest the historical executable to
source, or measure solver-step flux/source terms. Those limits remain.

## The fixed interior retains positive excess storage

At approximately 20 Myr, energies in the declared centre-zero potential,
divided by labelled bipolar power times actual age, are:

| Case | Fixed 50-kpc-inset box | R100 sphere | Whole grid | Outside fixed box |
| --- | ---: | ---: | ---: | ---: |
| C-LO | 1.157066 | 1.159289 | 10.465860 | 9.308794 |
| G-HI | 1.074883 | 1.074884 | 1.076584 | 0.001701 |

The fixed box therefore contains 15.71% and 7.49% more stored-energy change
than the label at these two case/ages. C-LO's large whole-grid excess lies
predominantly outside that box. The new R100/R300 component measurements
reproduce the accepted older spherical products within 1.42e-16 labelled-input
units; the new reduction did not change their energy arithmetic.
<!-- claims: NAT-09 -->

Full-cell membership makes the retained faces ±149.724228 kpc in x/y and
±198.935715 kpc in z, inside the nominal 50-kpc-inset faces. Current cocoon
cells and all cells with speed at least 30 km/s remain inside this box in both
pilots. Cells with thermodynamic changes of at least 1% also occur outside it
and reach the domain faces. These masks are operational diagnostics, not a
causal separation of jet effects and boundary artefacts. Neither containment
nor the coarse controls certify a quiet production interior. The pilot at
C-LO/20 does not resolve the late C-LO history by itself.

## The mass ledger makes the potential convention consequential

R100 mass changes, in grams, on the same current-region masks applied to
both initial and current cells are:

| Case | All cells | Current cocoon | Current ambient |
| --- | ---: | ---: | ---: |
| C-LO | −1.05105e40 | −1.13999e42 | +1.12948e42 |
| G-HI | +4.37089e41 | −2.17207e43 | +2.21578e43 |

For a potential shift Phi → Phi+c, total stored change shifts by c DeltaM.
The independently accumulated shifted gravitational term satisfies that
identity in every reported region. An illustrative c = +1e15 cm²/s² changes
R100's total ambient share from **97.52% to 105.32%** in C-LO and **53.55% to
55.17%** in G-HI. Values above unity are possible for signed contributions;
this is not a deposition efficiency. The same shift changes fixed-box total
storage by only −0.00095675 and +0.00034613 labelled-input units respectively,
because regional mass deficits and surpluses largely cancel in the total.
<!-- claims: NAT-09 -->

The shift is a convention sensitivity, not a physical uncertainty interval.
Ambient thermal-plus-kinetic shares remain 89.64% and 51.67% for the two R100
pilots. The old headline ambient share of total energy remains retired;
mass is now measured for these two case/ages, not the full four-case history.

## The first flux interval cannot locate an in-grid energy source

G-LO's initial and next saved states are separated by 0.999659684 Myr.
All saved initial surface fluxes are zero; at the later endpoint, reconstructed
net outward nozzle-control power is 1.04645–1.05972 times labelled bipolar
power across the padding/reconstruction cases. That is a control-surface
diagnostic, not the actual overwrite or discrete Riemann delivery.

The whole-grid inferred source is storage change plus outward face transport.
Subtracting the analogous nozzle-control balance gives the unresolved
outside-nozzle balance. Its startup value is dominated by the assumed time
quadrature:

| Quadrature | Whole-grid source / label | Nozzle-control source / label | Outside-nozzle residual / label |
| --- | ---: | ---: | ---: |
| Left rectangle | 1.09242 | 0.01159–0.02807 | 1.06434–1.08083 |
| Trapezoid | 1.07600–1.08219 | 0.53482–0.55793 | 0.51807–0.54738 |
| Right rectangle | 1.05958–1.07197 | 1.05804–1.08779 | −0.02821–0.01393 |

The trapezoid assigns half of the later saved endpoint flux across the first
saved interval. Its roughly half-label residual therefore cannot be called
measured numerical heating outside the nozzle. The sensitivity scenarios
include both residual signs and are not formal confidence or error bounds.
Full histories can clarify later intervals and accumulated cadence dependence;
they cannot recover the missing startup trajectory. Separate historical
gravity-update, floor and conversion-repair energies remain unidentified.
<!-- claims: BND-06 -->

## Continuation and evidence

After pilot acceptance, all eight immutable full requests were submitted as
jobs **879902–879909**, fixed then flux for C-LO, G-HI, C-HI and G-LO in that
order. An afterany chain serialises I/O; it does not imply a failed parent
would be scientifically accepted. At **13:03:29 AEDT**, the first job was
queued for compatible capacity and the remaining seven were dependency-held.
Completion/abort mail and the recipient were verified for every job.
Requests cover 0–50 in C-HI/C-LO/G-LO and retained 0–47 in G-HI. Only existing
outputs are analysed; no PLUTO simulation or emission-cohort job was started.

The [compact evidence](assets/turn18_pilot_review_2026-11-14/README.md) includes
the fixed/mass summaries, full startup scenarios, independent-check verdicts,
hashes and private archive restoration commands. Source remains **8177795**;
native, scientific and frozen-emission gates are unchanged. Claims NAT-09 and
BND-06 are provisional, and BND-05 remains provisional. The article and brief
are not revised by this pilot acceptance.
