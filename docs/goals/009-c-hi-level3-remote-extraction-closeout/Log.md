# Log: Goal 009 C-HI Level 3 Remote Extraction Closeout

## 2026-06-18 - orchestrator packet

X-ray Cavities opened Goal 009 after accepting and publishing Goal 008 as:

```text
8ac4b43 Add blocked C-HI Level 3 ambient energy package
```

Goal 008 result status was:

```text
blocked_remote_postprocessing_access
```

The useful next step is bounded existing-output post-processing, not new
simulation work. Goal 009 is constrained to remote access/staging, execution of
the tested Level 3 thermal/kinetic extractor on the existing `C-HI`
baseline/final HDF5 pair, and compact local packaging if outputs are available.

Important inherited constraints:

- no PLUTO production run;
- no `48 h` or multi-day production job;
- no broadening to views, ages, `C-LO`, or `G-LO`;
- no gravitational-energy method invention without reviewed potential/profile
  convention;
- if a PBS post-processing job is submitted and verified queued/running, wake
  X-ray Cavities and stop without polling.

`jet` must wake X-ray Cavities when submitted, complete, or blocked, then stop.

## 2026-06-18 - jet start state

Start state after `git fetch --prune origin` and `git pull --ff-only`:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
99e883a
```

Repo-local `AGENTS.md` and the Goal 009 packet were read before project work.
The worktree was clean at start.

## 2026-06-18 - jet local prep and access blocker

Read the required Goal 009/Goal 008 context and confirmed the inherited method
state:

- Goal 008 thermal/kinetic extractor is locally tested.
- The accepted baseline/final remote HDF5 paths are identified.
- The prior remote preflight was dataset/shape-only; the extractor coordinate
  compatibility check still has to run on the full remote pair before values
  can be trusted.
- Gravitational Level 3 remains blocked unless a reviewed potential/profile
  convention appears inside authorized evidence.

Pre-remote local gate passed:

```text
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
..............                                                           [100%]
14 passed in 0.22s
```

Terminal SSH probes failed:

```text
ssh -o BatchMode=yes -o ConnectTimeout=12 kunanyi-via-deep hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).
Connection closed by UNKNOWN port 65535

ssh -o BatchMode=yes -o ConnectTimeout=12 kunanyi-via-nectar hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).
Connection closed by UNKNOWN port 65535
```

Before the steering correction below, the repo-local Safari helper opened the
Open OnDemand "Enable Jumpbox SSH" page and Safari showed an authenticated
5-minute jumpbox window. Retrying terminal SSH still failed with the same
permission error. The Open OnDemand dashboard also exposed a Safari web shell
on `kunanyi-00`, and a harmless `hostname; pwd` probe returned:

```text
<tpac-host>
/u/bwbrook
```

Operational steering then corrected the route: do not use Safari; use the
Chrome plugin / `@chrome` route for authentication and the 5-minute selector.
After that correction, no further Safari staging or remote action was used.

Chrome/plugin capability check:

- `tool_search` for Chrome/browser control exposed only the generic
  `mcp__node_repl` bridge and unrelated tools, not Chrome browser-control
  tools.
- `list_available_plugins_to_install` did not list
  `plugin://chrome@openai-bundled` or any Chrome plugin install candidate.
- A direct `nodeRepl.requestMeta` inspection showed no exposed Chrome plugin
  browser surface for this thread.

Result status:

```text
blocked_chrome_plugin_unavailable_for_ood_auth
```

No bounded PBS post-processing job was staged or submitted, so the PBS stop
rule was not invoked. No remote extraction ran and no thermal/kinetic Level 3
values were produced.

Local prep added a small bounded post-processing wrapper for the next
Chrome-authenticated staging attempt:

```text
scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs
```

The wrapper uses the accepted existing baseline/final HDF5 paths, runs
`scripts/science/pluto_h5_level3_ambient_extract.py` on one compute node, writes
compact CSV/provenance outputs under:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy
```

Validation after the blocker:

```text
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
..............                                                           [100%]
14 passed in 0.19s

bash -n scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs
<no output>

git diff --check
<no output>
```

Boundary confirmation: no new PLUTO production run, no broadening, no
multi-day/48 h production job, no PBS submission, no data extraction, no final
radio observable generation, no scientific-default change, no commit, and no
push occurred.

## 2026-06-18 - jet unblock correction and PBS submission

X-ray Cavities corrected the access interpretation:

- the Chrome/plugin route was available from the orchestrator thread and had
  already enabled the Open OnDemand 5-minute jumpbox window;
- raw `ssh -o BatchMode=yes ...` is not decisive for this password-auth route;
- the established secret-safe expect helpers should be used without printing
  secrets.

Resumed from the current dirty state. No Safari/Open OnDemand action was used
after the steering correction.

Verified the repo-local expect route through `kunanyi-via-deep`:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd'
<tpac-host>
/u/bwbrook
```

Staged the bounded extractor and PBS wrapper:

```text
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/pluto_h5_level3_ambient_extract.py
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/c_hi_final_level3_ambient_energy.pbs
```

Checksum evidence:

```text
00d4f10b729cd74982514f4dde52c8ef7f5ee7a2b1074305d479c99aa6cd26de  pluto_h5_level3_ambient_extract.py
3e84ff8a27571d1dac66b958390a97d924d17b9694262788380b98b66c8fdc97  c_hi_final_level3_ambient_energy.pbs
```

Remote wrapper syntax check:

```text
bash -n c_hi_final_level3_ambient_energy.pbs
<no output>
```

Submitted from the remote stage directory:

```text
cd /u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy
qsub c_hi_final_level3_ambient_energy.pbs
699326.kunanyi-ohpc
```

Queue verification:

```text
Job_Name = c_hi_l3amb
job_state = Q
queue = normal
ctime = Thu Jun 18 13:06:14 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=64gb
Resource_List.walltime = 04:00:00
etime = Thu Jun 18 13:06:14 2026
```

Result status:

```text
submitted_waiting_pbs_completion
```

PBS stop rule invoked. No polling was done after queue verification.

Expected remote outputs:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy/level3_extractor_output.csv
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy/remote_logs/
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/final_level3_ambient_energy_2026-06-18.tar.gz
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/c_hi_final_level3_ambient_energy.out
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/c_hi_final_level3_ambient_energy.err
```

Resume only after Barry reports the PBS completion email or X-ray Cavities
explicitly requests a re-check. Suggested resume command:

```bash
cd /Users/bwbrook/papers/xray_cavities
scripts/kunanyi/run_on_kunanyi.sh 'set -euo pipefail
cd /u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy
jobid=$(cat qsub_jobid.txt)
qstat -x -f "$jobid" | egrep "^(    Job_Name|    job_state|    queue|    Exit_status|    resources_used\\.|    Resource_List\\.(select|walltime)|    ctime|    etime|    mtime)"
ls -lh c_hi_final_level3_ambient_energy.out c_hi_final_level3_ambient_energy.err final_level3_ambient_energy_2026-06-18.tar.gz
sha256sum final_level3_ambient_energy_2026-06-18.tar.gz
find /scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy -maxdepth 2 -type f -printf "%P\t%s bytes\n" | sort'
```

## 2026-06-18 - jet completion retrieval and package

Barry reported the PBS completion email for `699326.kunanyi-ohpc`, and X-ray
Cavities explicitly authorized re-check/retrieval after refreshing the
Chrome/Open OnDemand jumpbox window.

Remote status check:

```text
Job_Name = c_hi_l3amb
resources_used.cpupercent = 30
resources_used.cput = 00:01:12
resources_used.mem = 150096kb
resources_used.ncpus = 1
resources_used.vmem = 423060kb
resources_used.walltime = 00:02:39
job_state = F
queue = normal
mtime = Thu Jun 18 13:08:53 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=64gb
Resource_List.walltime = 04:00:00
Exit_status = 0
```

Retrieved compact outputs:

```text
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_extractor_output.csv
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/remote_logs/final_level3_ambient_energy_2026-06-18.tar.gz
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/remote_logs/c_hi_final_level3_ambient_energy.out
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/remote_logs/c_hi_final_level3_ambient_energy.err
```

Remote stdout evidence:

```text
baseline_hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960)
final_hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960)
level3_extractor_validation=passed
```

Remote stderr is zero bytes. Retrieved archive checksum:

```text
77d01152913072afcfcf4a0ebffdb9d50a50afea8a25ddb9c311e04cb8cd1d96
```

Added package helper and focused test:

```text
scripts/science/build_final_level3_remote_extraction_closeout.py
tests/test_final_level3_remote_extraction_closeout.py
```

Generated package files:

```text
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_ambient_energy.csv
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_method_decisions.csv
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_metadata.json
docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md
```

Thermal/kinetic status:

```text
green_level3_thermal_kinetic_closeout
```

Overall status:

```text
partial_green_with_gravitational_blocker
```

Headline bipolar results:

```text
ambient_thermal_delta = 2.259405474647962e60 erg
ambient_kinetic_delta = 5.422582705702232e59 erg
ambient_thermal_plus_kinetic_delta = 2.8016637452181852e60 erg
```

Bipolar thermal-plus-kinetic ratios:

```text
Level 1 injected energy: 0.887793667838551
Level 2 tracer-lobe energy: 2.018280864459599
pV: 4.073337851104109
2.5pV: 1.6293351404416438
4pV: 1.0183344627760273
```

The coordinate-compatibility contract executed in the remote job: the
SHA-matched extractor validates baseline/final `X`, `Y`, and `Z` axes with
`rtol=0`, `atol=1e-10 kpc` before streaming subtraction, and the remote job
reached `level3_extractor_validation=passed`.

Gravitational Level 3 remains:

```text
blocked_missing_potential
```

No reviewed potential/profile zero-point convention is available inside
authorized evidence.

Boundary confirmation: no new PLUTO production run, no broadening, no
multi-day/48 h production job, no final radio observable generation, no
scientific-default change, no commit, and no push occurred.
