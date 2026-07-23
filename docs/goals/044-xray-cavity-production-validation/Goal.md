# Goal 044 - X-ray Cavity Production Validation

## Objective

Validate the complete observer-facing X-ray cavity pipeline used by Goals 040
and 041, using production-schema synthetic HDF5 fixtures and one accepted real
`C-HI` endpoint, without starting a new PLUTO production run.

## Required Path

`HDF5 rho/prs/tr1 -> XRAiSE emissivity -> projection -> corrected X-ray ->`
`tracer-blind radial residual -> physical-area cavity mask -> area/volume ->`
`hybrid pV/2.5pV/4pV summary`.

## Acceptance Contract

- Run the actual production XRAiSE CLI on nonuniform axisymmetric and
  non-axisymmetric fixtures.
- Preserve the existing automatic projection defaults.
- Add independent native-axis references: y integration at `0 deg` and x
  integration at `90 deg`.
- Compare the edge-overlap projector at `0/45/89.9/90 deg` with exact-axis
  references on common physical grids.
- Fail closed on conservation, continuity, empty columns, cavity recovery,
  energy conventions, provenance, or deterministic-rerun failures.
- Replay accepted `C-HI data.0051.flt.h5::Timestep_51` and compare direct and
  edge-overlap `90 deg` products with shared intensity normalization and
  absolute/fractional residuals.
- Deliver one compact archive containing a report-ready figure,
  machine-readable gate table, criteria, commands, hashes, metadata, and
  deterministic-rerun evidence.

## Boundaries

- Existing simulation outputs only; no PLUTO run.
- No lifecycle deletion, movement, truncation, or overwrite.
- Goal 041 products remain accepted provenance surfaces unless this validation
  fails a material gate.
- Goal 042 retains a validation hold on the real endpoint HDF5 and required
  X-ray intermediates. Goal 043 remains separately approval-gated.
- A submitted PBS job triggers the normal wake-and-stop rule after queued or
  running verification.
