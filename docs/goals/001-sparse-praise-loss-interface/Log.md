# Log: Goal 001 Sparse PRAiSE-Compatible Loss Interface

## 2026-06-11 - X-ray Cavities

Goal packet created by the project orchestrator.

Initial orchestration context:

- Barry approved Goal 001 as a local implementation plus tests.
- Remote staging and Kunanyi access are explicitly out of scope.
- `jet` must send a wake-up to X-ray Cavities when complete or blocked.
- `jet` must not commit or push.

Starting state before goal-packet creation:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD e29606e
```

No project implementation work has been done by the orchestrator.

## 2026-06-11 - jet starting state

Started local-only implementation sprint from the goal packet.

Starting state checked before edits:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 763c9b2
```

Working tree was clean before goal edits. The launch HEAD differs from the
packet's expected `e29606e`, but the repo is clean and even with `origin/main`,
consistent with a pre-delegation fast-forward by X-ray Cavities.

## 2026-06-11 - jet implementation and validation

Implemented the local sparse PRAiSE-compatible loss-table interface inside
`scripts/science/sparse_particle_radio_bridge.py`.

Changed files:

- `scripts/science/sparse_particle_radio_bridge.py`
- `tests/test_sparse_particle_radio_bridge.py`
- `docs/science/sparse_praise_loss_interface_2026-06-11.md`
- `docs/goals/001-sparse-praise-loss-interface/Log.md`

Design decisions:

- The default pressure-history proxy path is preserved and labelled with
  `loss_model_key = pressure_history_proxy`.
- The external path is selected only with `--loss-table` and is labelled with
  `loss_model_key = external_praise_compatible`.
- External loss tables are keyed by selected particle `id`, not row order.
- CSV is the default; `.tsv` and `.tab` use tab delimiters.
- Missing selected IDs, duplicate IDs, non-integer IDs, non-finite loss
  factors, and negative loss factors fail fast.
- External factors are required to be finite and non-negative, but are not
  clipped to `0..1`, because the earlier PRAiSE smoke path produced factors
  above `1`.

TDD checkpoint:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py -q
initial result after adding tests: 5 failed, 2 passed
failure reason: --loss-table was not yet implemented
```

Focused post-implementation check:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py -q
7 passed in 0.37s
```

Required validation gate:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
9 passed in 0.53s
```

PBS wrapper validation was not run because no PBS wrapper was touched.

Current git status after validation:

```text
## main...origin/main
 M docs/goals/001-sparse-praise-loss-interface/Log.md
 M scripts/science/sparse_particle_radio_bridge.py
 M tests/test_sparse_particle_radio_bridge.py
?? docs/science/sparse_praise_loss_interface_2026-06-11.md
```

Residual risks:

- The external table path is validated against deterministic local fixtures,
  not a newly generated production PRAiSE sparse loss table.
- The output is still an interface/provenance product and must not be treated
  as a final PRAiSE science radio map.
- Final grid/tracer volume coupling and the observable comparison page remain
  follow-up work.

## 2026-06-11 - jet review iteration

X-ray Cavities reviewed the core Goal 001 diff and requested a narrow
test-coverage iteration before acceptance.

Added tests in `tests/test_sparse_particle_radio_bridge.py` for:

- tab-delimited `.tsv` external loss tables with custom
  `--loss-id-column` and `--loss-factor-column` names;
- non-integer particle IDs in external loss tables;
- missing configured external-table columns with custom column names.

No implementation change was required for this iteration; the current
interface already supported the documented delimiter and custom-column
contract. No science-note wording change was required.

Focused check:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py -q
10 passed in 0.52s
```

Required validation gate:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
12 passed in 0.67s
```

Current git status after review iteration:

```text
## main...origin/main
 M docs/goals/001-sparse-praise-loss-interface/Log.md
 M scripts/science/sparse_particle_radio_bridge.py
 M tests/test_sparse_particle_radio_bridge.py
?? docs/science/sparse_praise_loss_interface_2026-06-11.md
```

Scope guard: no remote work, PRAiSE run, PBS work, cleanup, commits, pushes,
or generated data workflows were performed.
