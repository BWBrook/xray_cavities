# Plan: Goal 012

## Phase 1 - Start Clean And Confirm Evidence

- Fast-forward to `origin/main`.
- Record `pwd`, branch, short HEAD, and status in `Log.md`.
- Read the required Goal 012 evidence.
- Confirm Goal 011 is accepted at the current repository state and provides the
  final `45 deg` product to compare against.

## Phase 2 - Choose The Lightest Viable Product Path

- Reuse the Goal 011 projection machinery where possible.
- Decide whether the `90 deg` final endpoint can be produced locally from
  existing compact assets.
- If full-grid data are required, prepare a bounded Kunanyi post-processing
  wrapper and stop after verified PBS submission.

## Phase 3 - Implement Narrowly

- Add or extend only helper code needed for the final `90 deg` product and
  `0/45/90 deg` packaging.
- Preserve accepted science defaults and comparator conventions.
- Keep the product language aligned with Goal 011:
  - projection-sensitivity probe;
  - topology caveat;
  - radio diagnostic caveat;
  - Level 3 gravity tracked gap.
- Keep `0`, `45`, and `90 deg` comparison explicit.

## Phase 4 - Validate

- Run focused tests for changed local helper code.
- Run `bash -n` for any changed PBS wrapper.
- Parse generated CSV/JSON outputs.
- Run `git diff --check`.
- If a PBS job is submitted, validate staging hashes and queue/running state,
  then wake and stop.

## Phase 5 - Package Or Stop

If complete product:

- create the dated science note and compact asset directory;
- include a `0/45/90 deg` scalar table and reviewer-facing visual;
- update the exchange log, current status, and Goal 012 log;
- wake X-ray Cavities with product paths and validation.

If submitted:

- record job id, queue state, staged paths, expected outputs, and exact
  retrieval instructions;
- wake X-ray Cavities and stop without polling.

If blocked:

- preserve useful preparation;
- state the smallest concrete blocker and next action required.
