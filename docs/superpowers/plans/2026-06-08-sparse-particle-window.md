# Sparse Particle Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded PLUTO particle-window extractor that reads selected particle `.dbl` files directly and emits compact trajectory/lifecycle summaries without creating a dense all-history particle HDF5 cache.

**Architecture:** Keep the first version self-contained in a science script so it can be staged easily to Kunanyi. The tool reads a target particle file to choose deterministic tracer-bearing particle IDs, streams only requested output indices, writes long-format selected trajectories, and records per-output plus per-ID summaries.

**Tech Stack:** Python 3.12, NumPy, pytest, PBS/Anaconda3 on Kunanyi.

---

### Task 1: Tests For Sparse Window Selection

**Files:**
- Create: `tests/test_pluto_particle_sparse_window.py`
- Create: `scripts/science/pluto_particle_sparse_window.py`

- [ ] **Step 1: Write the failing tests**

Create synthetic PLUTO particle `.dbl` files with a valid ASCII header and little-endian float64 payload. Test that the sparse-window command:

- selects particles from the target output using tracer/density/pressure filters
- deterministically caps selected IDs with `--max-selected-ids`
- writes trajectory rows only for selected IDs
- writes per-ID lifecycle coverage across requested outputs
- writes per-output full-file side counts

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
uv run pytest tests/test_pluto_particle_sparse_window.py -q
```

Expected: fail because `scripts/science/pluto_particle_sparse_window.py` does not exist yet.

- [ ] **Step 3: Implement the minimal script**

Create `scripts/science/pluto_particle_sparse_window.py` with:

- header parsing based on `# field_names`, `# field_dim`, `# nparticles`, `# time`, `# stepNumber`, and `# endianity`
- binary payload offset from file size minus `nparticles * total_width * 8`
- CLI arguments `--output-dir`, `--particle-dir`, `--target-index`, `--start-index`, `--end-index`, `--stride`, `--max-selected-ids`, `--tracer-threshold`, and `--code-time-per-myr`
- outputs `particle_sparse_window_metadata.json`, `particle_sparse_window_summary.csv`, `particle_sparse_window_side_summary.csv`, `particle_sparse_window_lifecycle.csv`, and `particle_sparse_window_trajectory.tsv`

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_pluto_particle_sparse_window.py -q
```

Expected: all tests pass.

### Task 2: Kunanyi Wrapper And Handoff Docs

**Files:**
- Create: `scripts/kunanyi/c_hi_fullgrid_final_particle_sparse_window.pbs`
- Create: `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
- Create: `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-sparse-window.md`
- Modify: `docs/exchange/current_status.md`

- [ ] **Step 1: Add the PBS wrapper**

The wrapper should run the new script against the completed C-HI endpoint output directory with:

- `target-index = 5000`
- `start-index = 4950`
- `end-index = 5000`
- `stride = 5`
- `max-selected-ids = 20000`
- `tracer-threshold = 5e-3`
- `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`

- [ ] **Step 2: Run syntax checks**

Run:

```bash
bash -n scripts/kunanyi/c_hi_fullgrid_final_particle_sparse_window.pbs
python3 -m py_compile scripts/science/pluto_particle_sparse_window.py
git diff --check
```

- [ ] **Step 3: Stage and submit on Kunanyi**

Stage with checksum verification, submit with `qsub`, and capture PBS result, stdout/stderr, output file list, archive SHA, and headline summary values.

- [ ] **Step 4: Document results**

Record the job result, output locations, archive hash, selected-ID count, window coverage, and interpretation in the science report and exchange log.
