# Plan: Goal 011

## Phase 1 - Start Clean And Confirm Evidence

- Fast-forward to `origin/main`.
- Record `pwd`, branch, short HEAD, and status in `Log.md`.
- Read the required Goal 011 evidence.
- Confirm the key review decisions:
  - Stas-agent `Q-016`: proceed; gravity convention is not required first for
    the broadening step.
  - Patrick-agent `Q-017`: proceed with changes; preserve topology,
    radio-observable, and PBS guardrails.

## Phase 2 - Choose The Lightest Viable Product Path

- First try to reuse existing Goal 005/007/009 code and provenance patterns.
- Decide whether the `45 deg` final endpoint can be produced locally from
  existing compact assets.
- If full-grid data are required, prepare a bounded Kunanyi post-processing
  wrapper and stop after verified PBS submission.

## Phase 3 - Implement Narrowly

- Add or extend only the helper code needed for the final `45 deg` product.
- Preserve accepted science defaults and comparator conventions.
- Keep the visual/product language aligned with Goal 007:
  - wide-field context;
  - cavity-focused interpretation where possible;
  - topology caveat;
  - radio diagnostic caveat.
- Keep `45 deg` versus `0 deg` comparison explicit.

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
- update the exchange log, current status, and Goal 011 log;
- wake X-ray Cavities with product paths and validation.

If submitted:

- record job id, queue state, staged paths, expected outputs, and exact
  retrieval instructions;
- wake X-ray Cavities and stop without polling.

If blocked:

- preserve any useful local preparation;
- state the smallest concrete blocker and the next action required.
