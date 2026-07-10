# X-ray Cavities Data Lifecycle Strategy

Date: 2026-07-10

## Purpose

The three-case production programme now generates terabyte-scale raw PLUTO
outputs, while the durable scientific record is usually a much smaller set of
accepted restart surfaces, selected age-axis sources, processed arrays,
figures, tables, and provenance. Goal 038 demonstrated that ad hoc retention is
not sustainable: scratch filled before a valid G-LO continuation could even be
staged.

The project will therefore use a **promote, prove, then prune** lifecycle. Raw
data are retained because a stated dependency still needs them, not merely
because they exist. Processed products are accepted before their unique source
data become deletion candidates, and every destructive action is driven by a
machine-readable keep/delete ledger.

## Data Classes

The authoritative classes are in `data_classes.csv`:

1. **Raw checkpoint**: full fluid HDF5/XMF and particle restart payloads
   generated during active production. These live on scratch and are not Git
   artifacts.
2. **Restart-essential tuple**: the exact fluid HDF5/XMF, `restart.out`,
   particle restart, catalogues, executable/configuration hashes, and logs
   needed for a proven continuation. During an active chain retain at least the
   current and preceding validated tuples.
3. **Age-axis source**: selected float HDF5 and particle snapshots required to
   regenerate X-ray, radio, topology, or energy products. These remain raw
   science dependencies until each named method lane is accepted or explicitly
   abandoned.
4. **Processed science product**: validated maps, arrays, tables, metrics, and
   figures derived from raw sources. Compact products may live in Git; large
   processed products require a sanctioned archive plus a repo manifest and
   compact summary.
5. **Immutable provenance**: qstat, stdout/stderr, configuration, source and
   asset hashes, inventories, validation summaries, and decision notes. This is
   the permanent audit trail and should be compact enough for the repo.
6. **Invalid or duplicate payload**: zero-byte failed staging roots or
   byte-identical duplicates whose canonical retained copy is proven. These may
   be deleted mechanically after the ledger and collision checks pass.
7. **Quarantined partial payload**: a unique nonzero incomplete science file.
   It must be isolated from restart/product selection and retained until Barry
   approves deletion or a sanctioned archive/quarantine disposition.

Raw does not mean permanent; processed does not mean disposable. The class and
active dependencies determine retention.

## Lifecycle

Every significant payload moves through the states in `lifecycle_states.csv`:

```text
DISCOVERED -> VALIDATED -> PROMOTED -> ACCEPTED -> SUPERSEDED
                                              -> ARCHIVED
SUPERSEDED or ARCHIVED -> DELETE_APPROVED -> DELETED
```

`PROMOTED` means a canonical copy has been selected and its dependencies are
recorded. `ACCEPTED` means the product or restart surface passed the relevant
science/operational gate. `ARCHIVED` requires a real sanctioned archive with a
verified checksum; it must never be inferred from intent. `SUPERSEDED` means a
newer accepted surface provides the same role. Deletion is a separate state,
not an automatic consequence of supersession.

## Dependency Ledger

Before any general cleanup, create a per-file or homogeneous-file-group ledger
with at least:

- canonical path, case, run, output index, byte size, and SHA-256;
- data class and lifecycle state;
- canonical-copy path for duplicates;
- restart, source-age, radio, X-ray/topology, Level 3, and comparison-case
  dependency flags;
- processed products proven to derive from the source;
- archive location and checksum, if one exists;
- proposed action, reason, approval authority, executor, and timestamp.

A cleanup tool must fail closed on missing dependencies, partial promotion,
destination collision, hash mismatch, or an unrecognised file. It must write
pre/post inventories and be idempotent. The Goal 038 compactor embodies these
properties for one exact historical layout, but it is deliberately not the
generic implementation of this policy.

## Retention Milestones

The default milestones are recorded in `retention_milestones.csv`.

- During production, retain two validated restart generations and all compact
  catalogues/provenance.
- At endpoint acceptance, retain the endpoint tuple plus one prior known-good
  restart until endpoint integrity and first products are accepted.
- Retain only the explicit age-axis HDF5/particle sources selected by the
  sampling plan, rather than every transient checkpoint.
- Once all products depending on a unique raw source are accepted, and no
  active science hold remains, mark the source `SUPERSEDED` and prepare a
  deletion packet.
- Prefer migration to a sanctioned archive before deleting unique raw science
  data. No such writable project archive is currently proven, so scratch
  deletion remains approval-controlled.

## Deletion Authority

Agents may automatically delete only:

- zero-byte failed staging roots; and
- byte-identical duplicates after the canonical copy, its checksum, and all
  dependencies are validated.

A unique nonzero partial or corrupt scientific payload is quarantined, not
automatically deleted. Its removal requires Barry's explicit approval.

Deleting any unique scientific source data requires Barry's explicit approval,
even when the data are marked `SUPERSEDED`. The approval packet must quantify
bytes recovered, list every keep/delete class, identify unresolved science
holds, and include a tested rollback or reacquisition statement where one is
possible.

## Scratch Capacity Gate

Every production or high-volume post-processing submission must estimate:

```text
forecast growth = raw outputs + particle outputs + transient staging
                  + archive duplication + 20 percent safety
```

The gate in `scratch_gate_policy.csv` uses verified manifest bytes and a real
write probe. Recursive `du` is supporting evidence only because sparse files,
symlinks, and service behavior can make it misleading.

- **GREEN**: write probe passes and known free headroom is at least 1.5 times
  forecast growth. Submit under normal controls.
- **AMBER**: write probe passes and headroom is 1.1 to less than 1.5 times the
  forecast. Submission requires a restart-safe job, an explicit closeout
  compaction plan, and project-lead acceptance of the margin.
- **RED**: write probe fails, inventory is untrusted, or headroom is below 1.1
  times forecast. Do not submit until capacity is repaired.

Goal 038 predates adoption of this prospective gate and is recorded as an
explicit exception, not retroactively labelled green or amber. Its reclaimed
2.810 TB is only marginally above the HDF5-only estimate after applying the
20 percent safety factor, before particle/log growth; under this new policy the
available evidence would be `RED` or unquantified. The already-submitted job is
restart-safe and watchdog-guarded, but no future large submission may rely on
the same capacity evidence without a verified free-headroom forecast.

## Current Science Holds

The current holds are in `current_science_holds.csv`:

- radio particle/raytracing methodology is not frozen, so radio-relevant
  particle source snapshots remain protected;
- final observational X-ray topology is conditional, so source HDF5 needed for
  a bounded topology rerun remains protected;
- Level 3 gravitational energy lacks an accepted potential convention, so the
  baseline and final endpoint surfaces remain protected; and
- the C-HI/C-LO/G-LO comparison is not complete, so accepted case endpoints and
  first-product source surfaces remain protected.

These holds can be retired by an accepted method or an explicit project
decision. They are not permanent excuses to retain every intermediate file.

## Operational Cadence

1. **Before qsub**: produce the byte forecast, dependency-aware retention
   inventory, gate colour, and no-overwrite check.
2. **After PBS completion**: validate endpoint/checkpoint integrity and write a
   compact provenance package before launching dependent analysis.
3. **After product acceptance**: promote canonical processed products and
   update raw-source dependencies.
4. **At case closeout**: prepare a deletion packet for superseded raw data,
   obtain the required approval, execute fail-closed, and verify the post-state.
5. **Quarterly or before the next large run**: audit scratch by lifecycle state,
   not merely by directory age.

This makes large production runs the normal scientific workflow while keeping
scratch a managed working store rather than an accidental archive.

## Assets

Machine-readable policy assets live under:

```text
docs/science/assets/xray_cavities_data_lifecycle_strategy_2026-07-10/
```

They include data classes, lifecycle states, retention milestones, scratch
gates, current science holds, and metadata.
