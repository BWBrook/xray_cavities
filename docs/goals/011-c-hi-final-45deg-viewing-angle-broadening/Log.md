# Log: Goal 011 C-HI Final 45-Degree Viewing-Angle Broadening

## 2026-06-23 - orchestrator launch packet

X-ray Cavities reviewed the newly pushed collaborator-agent responses:

- Patrick-agent `Q-017`: `PROCEED WITH CHANGES` for one narrow
  post-processing-only `C-HI` broadening step, preserving topology,
  radio-observable, and large-PBS guardrails.
- Stas-agent `Q-016`: `PROCEED TO CONTROLLED BROADENING`; gravitational Level
  3 convention is not required before the first broadening step, and updated
  energy calculations should be handled in post-processing.
- Stas-agent also answered earlier `Q-003`, `Q-004`, and `Q-005`, confirming
  that midplane snapshots, length/volume evolution, radio/X-ray observables,
  and energy fractions remain important validation themes, but radio luminosity
  and energetics can be adjusted in post-processing.

Orchestrator decision: open the first actual controlled broadening goal as
final `C-HI`, `45 deg`, post-processing-only. This is intentionally one viewing
angle at one endpoint, not a `45/90 deg` batch, source-age sweep, `C-LO`,
`G-LO`, or new PLUTO production run.

Action repo state at packet creation:

```text
git fetch --prune origin
git merge --ff-only origin/main
Fast-forwarded to fb9bda5

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
fb9bda5
```

`jet` must wake X-ray Cavities when complete, blocked, or after any required PBS
job is submitted and verified queued/running.

## 2026-06-23 - jet start state

Start state after the requested sync:

```text
cd /Users/bwbrook/papers/xray_cavities
git fetch --prune origin
git merge --ff-only origin/main
Already up to date.

pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
f39ce61
```

Repo-local `AGENTS.md` and the Goal 011 packet were read before project work.
The worktree was clean at start.

## 2026-06-23 - evidence read and path decision

Read the required Goal 011 evidence inside the repo, including:

- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`
- `agent_comms/threads/2026-05-11-onboarding-and-current-state.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
- `docs/goals/007-c-hi-observational-product-readiness-gate/Log.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Log.md`
- `docs/goals/010-c-hi-level3-broadening-decision-packet/Log.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`

Decision basis confirmed:

- Stas-agent `Q-016`: `PROCEED TO CONTROLLED BROADENING`; gravity convention
  is not required first for the broadening step, and energy-accounting details
  should be handled in post-processing.
- Patrick-agent `Q-017`: `PROCEED WITH CHANGES` for one narrow
  post-processing-only `C-HI` broadening step, preserving topology,
  radio-observable, and large-PBS guardrails.

Path decision: no local committed `45 deg` final endpoint assets exist. A real
45-degree X-ray/tracer projection requires bounded full-grid post-processing on
the existing final HDF5 output. Therefore Goal 011 should stop in
`submitted_waiting_pbs_completion` after one queued/running verification, per
the PBS stop rule.

## 2026-06-23 - local implementation and validation

Changed:

- `scripts/science/xraise_grid_smoke.py`
  - added explicit non-default projected-view support:
    `--view-angle-deg` and `--projected-u-bins`;
  - default `0 deg` y-axis projection remains the default code path.
- `tests/test_xraise_grid_smoke_projection.py`
  - added focused projection-axis and path-weight tests.
- `scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs`
  - added bounded Goal 011 final-endpoint `45 deg` post-processing wrapper.

Local validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py -q
...                                                                      [100%]
3 passed in 0.36s

bash -n scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs
<no output>

git diff --check
<no output>
```

## 2026-06-23 - remote staging and PBS submission

Initial helper probe failed because the TPAC SSH selector window had expired:

```text
MFA check failed. Please login and activate SSH access via the web portal again.
```

Used Chrome/Open OnDemand only for the authorized TPAC 5-minute selector. The
portal reported:

```text
You have a 5.0 min window which closes at Tue Jun 23 17:52:39 2026 to ssh to <tpac-host>.
```

Repo-local Kunanyi helper then succeeded:

```text
<tpac-host>
/u/bwbrook
```

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening
```

Local SHA-256 values:

```text
551bf8b0ab49b1d996eef2384239d221a430566125274df7e8979bd0dc29ec13  scripts/science/xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  scripts/science/pluto_h5_cavity_stub_extract.c
588bbe7c4ae95da4c58039c3b2f971666db8547ca79baaaeeebff92d5c2df204  scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs
```

Remote staged SHA-256 values matched:

```text
551bf8b0ab49b1d996eef2384239d221a430566125274df7e8979bd0dc29ec13  xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  pluto_h5_cavity_stub_extract.c
588bbe7c4ae95da4c58039c3b2f971666db8547ca79baaaeeebff92d5c2df204  c_hi_final_45deg_viewing_angle_broadening.pbs
```

Remote wrapper syntax:

```text
cd /u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle
bash -n c_hi_final_45deg_viewing_angle_broadening.pbs
<no output>
```

Submitted PBS job and verified queued:

```text
job_id=699815.kunanyi-ohpc
Job_Name = c_hi_xcav45
job_state = Q
queue = normal
ctime = Tue Jun 23 17:49:18 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Expected outputs:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening/xraise_grid_45deg/
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening/cavity_stub/
```

Resume instruction: do not poll. Resume only after Barry reports the PBS
completion email or X-ray Cavities explicitly requests a re-check. The next
resume should retrieve the compact archive, package a local `45 deg` versus
accepted `0 deg` comparison product, and preserve the X-ray topology,
radio-diagnostic, Level 3 gravity tracked-gap, and `pV`/`2.5pV`/`4pV` caveats.

Important packaging caveat: `cavity_stub/cavity_ellipse_boundary_0deg.tsv`
remains the extractor's 0-degree projected boundary. A final 45-degree visual
overlay should project the 3D cavity geometry from the summary rows into the
45-degree sky plane rather than treating that file as a 45-degree boundary.

Final status for this turn:

```text
submitted_waiting_pbs_completion
```

Boundary confirmation: no new PLUTO production simulation, no `90 deg`, no
source-age sweep, no `C-LO`, no `G-LO`, no broad batch, no multi-day production
commitment, no scientific-default change, no commits, and no pushes occurred.
The PBS stop rule was invoked immediately after queued-state verification.

## 2026-06-23 - completion resume and local package

Barry reported the PBS completion email for `699815.kunanyi-ohpc`:

```text
Exit_status=0
resources_used.walltime=00:16:46
resources_used.cput=00:11:32
resources_used.mem=1260168kb
```

Retrieved the completed archive and stage logs with the repo-local
`fetch_from_kunanyi.sh` helper:

```text
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/remote_logs/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_45deg_viewing_angle_broadening.out
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_45deg_viewing_angle_broadening.err
```

Remote stdout evidence:

```text
hdf5_preflight=passed
xray_45deg_validation=passed
cavity_validation=passed
archive_sha256=fbf5102046b103e2777c8e29b85eee08dc5f5ff028196e5f6bcb73dc48f0ee20
finished_utc=2026-06-23T08:06:05Z
```

Remote stderr is zero bytes.

Added the local closeout packager and product:

- `.gitattributes`
  - added the Goal 011 asset bundle to the byte-preserved review artefact
    rules.
- `scripts/science/build_final_45deg_viewing_angle_broadening.py`
  - validates the fetched 45-degree X-ray metadata and remote markers;
  - packages the accepted `0 deg` versus new `45 deg` comparison;
  - projects the 3D cavity ellipsoid rows into the 45-degree `u-z` sky plane
    instead of reusing `cavity_ellipse_boundary_0deg.tsv`.
- `tests/test_final_45deg_viewing_angle_broadening.py`
  - verifies projected boundary construction and rejects non-45-degree target
    metadata.
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/`

Primary package outputs:

```text
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/c_hi_final_45deg_viewing_angle_broadening.png
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/viewing_angle_comparison.csv
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/projection_metrics.csv
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/cavity_energy_convention.csv
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/product_provenance.csv
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/final_45deg_viewing_angle_metadata.json
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/cavity_stub/cavity_ellipse_boundary_45deg.tsv
```

Headline scalar comparison:

- corrected X-ray max: `45/0 = 0.11475003428628802`
- corrected X-ray pixel sum: `45/0 = 0.44636214774306926`
- bipolar cavity convention carried forward:
  - `pV = 6.87805393912703e59 erg`
  - adopted `2.5pV = 1.7195134847817575e60 erg`
  - `4pV = 2.751221575650812e60 erg`

Final status for this goal:

```text
complete_product
```

Boundary confirmation for completion resume: retrieved existing compact
outputs only; no new PBS submission, no new PLUTO production, no `90 deg`, no
source-age sweep, no `C-LO`, no `G-LO`, no broad batch, no scientific-default
change, no commits, and no pushes occurred.
