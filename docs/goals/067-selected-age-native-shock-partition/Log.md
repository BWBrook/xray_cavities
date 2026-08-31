# Goal 067 log

## 2026-08-31 - method frozen and local implementation green

- Frozen the selected-age native three-dimensional shock-energy method before
  inspecting any Goal 067 output.
- Kept no-jet controls in their defensible role: dimensionless threshold
  calibration only, because their grid is coarser than the production grid.
- Implemented a native-grid, same-cell `t=0` reference ledger with Stas's
  centre-zero fixed potential convention.
- Defined the shock region as the ambient entropy-excess component connected
  in 3D to a compressed axial-front seed. Missing, non-supersonic,
  unsupported, boundary-touching, and front-mismatched cases fail closed.
- Prespecified threshold factors `0.5/1/2`, with factor `1` primary, and
  side-specific reporting before any bilateral sum.
- Prespecified the full accepted selected-age surface in one job rather than a
  sequence of exploratory rungs. `G-HI/50` remains excluded.
- Added compact-output and no-overwrite PBS machinery. Transient native-grid
  caches and masks are not archived.

Local validation:

```text
uv run pytest tests/test_selected_age_native_shock_wrapper.py tests/test_selected_age_native_shock.py tests/test_snapshot_shock_energy.py -q
9 passed in 0.27s

bash -n scripts/kunanyi/four_case_selected_age_native_shock.pbs
passed
```

Remote preflight resolved one inherited path irregularity: the cluster no-jet
HDF5 files are retained in the run's `problem/` directory, while the group
files are in `problem/outputs/`. Both six-snapshot series are complete,
readable, single-timestep HDF5 files with shape `500 x 400 x 400`.

Staging and preflight:

- stage root:
  `/u/bwbrook/codex_kunanyi/goal067_selected_age_native_shock`;
- analysis root:
  `/u/bwbrook/xray_cavities_analysis/2026-08-31-selected-age-native-shock`;
- stage archive SHA-256:
  `8e5116a62ad1efde321064329ddc19a13bd102b868920299acca42043adee565`;
- all staged hashes, remote wrapper syntax, Anaconda
  `h5py/numpy/scipy` imports, environment tables, accepted shock tables, and
  all `19` selected production HDF5 surfaces passed;
- the `normal` queue is enabled and started and permits `48:00:00` walltime.

The first submission attempt encountered an expired five-minute TPAC selector
before any remote scheduler command ran. The selector was refreshed and the
single job was then submitted successfully:

```text
job_id=789812.kunanyi-ohpc
Job_Name=shock_energy
job_state=Q
queue=normal
Resource_List.select=1:ncpus=2:mpiprocs=1:mem=128gb
Resource_List.walltime=48:00:00
qtime=Mon Aug 31 20:40:19 2026
```

Expected completion surfaces:

- archive:
  `/u/bwbrook/codex_kunanyi/goal067_selected_age_native_shock/four_case_selected_age_native_shock_2026-08-31.tar.gz`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal067_selected_age_native_shock/four_case_selected_age_native_shock.out`
  and `.err`;
- compact case outputs under the analysis root, including
  `native_shock_energy_selected_age.csv` and control-calibration tables.

Status: `submitted_waiting_pbs_completion`.

The PBS stop rule is active. Resume only after Barry reports the completion
email or explicitly authorizes a re-check.

## 2026-08-31 - immediate launch failure repaired once and resubmitted

Barry reported that `789812.kunanyi-ohpc` failed immediately. The authorized
completion check found `F/2`, zero CPU time, zero memory, and zero walltime.
Remote stderr identified the first failure exactly:

```text
/var/spool/pbs/mom_priv/jobs/789812.kunanyi-ohpc.SC: line 74: declare: -n: invalid option
```

Kunanyi runs Bash `4.2.46`, which supports the existing arrays and `mapfile`
but not Bash namerefs. No calibration or production HDF5 analysis had started.
The original failed stage, stdout/stderr, and empty analysis root were left
untouched.

The wrapper now checks the cluster and group control-array counts explicitly,
without `declare -n`. A regression test bans that construct. The repair uses
fresh no-overwrite paths:

- stage root:
  `/u/bwbrook/codex_kunanyi/goal067_selected_age_native_shock_r1`;
- analysis root:
  `/u/bwbrook/xray_cavities_analysis/2026-08-31-selected-age-native-shock-r1`;
- archive:
  `/u/bwbrook/codex_kunanyi/goal067_selected_age_native_shock_r1/four_case_selected_age_native_shock_r1_2026-08-31.tar.gz`.

Repair validation:

```text
uv run pytest tests/test_selected_age_native_shock_wrapper.py tests/test_selected_age_native_shock.py tests/test_snapshot_shock_energy.py -q
9 passed in 0.25s

bash -n scripts/kunanyi/four_case_selected_age_native_shock.pbs
passed

remote Bash version
4.2.46(2)-release

remote staged sha256sum --check
all inputs passed
```

Exactly one repaired job was submitted:

```text
job_id=789813.kunanyi-ohpc
Job_Name=shock_energy
job_state=Q
queue=normal
Resource_List.select=1:ncpus=2:mpiprocs=1:mem=128gb
Resource_List.walltime=48:00:00
qtime=Mon Aug 31 20:58:32 2026
```

Status: `repair_submitted_waiting_pbs_completion`.

The PBS stop rule is active for `789813`; no polling occurred after queued
verification.

## 2026-08-31 - repaired run recovered without HDF5 recomputation

Barry reported that `789813.kunanyi-ohpc` completed with `Exit_status=1` after
`01:46:45`. Final scheduler evidence retained `job_state=F`,
`Stageout_status=1`, `cput=02:39:08`, `mem=38023516kb`, and `ncpus=2`.

The first failure was a post-analysis schema typo in the wrapper validator:

```text
KeyError: 'volume_kpc3'
```

The frozen output schema correctly uses `mask_volume_kpc3`. All four science
workers had already exited `0`; their metadata report
`complete_selected_age_native_shock_partition`, and the complete `171`-row
surface was present. The wrapper validator and regression test now use the
correct field.

A no-rerun file-list finalizer validated the existing compact results and
created a clean 39-member archive. No production HDF5 input was reopened.
Archive SHA-256:
`1287c74a2a9c2891ba2feb6d641128460f9a546828e2380daed901c40b73182d`.

Local closeout validation produced `19` primary case-age rows: `15`
quantitative and four explicitly unresolved late `C-LO` rows. Both no-jet
control gates passed. The Goal 066 joins contain `19` native rows and `464`
observer-method rows without changing their accepted validity flags.

Decision:
`SELECTED_AGE_NATIVE_SHOCK_PARTITION_GREEN_C_LO_LATE_FAIL_CLOSED`.

Status: `complete_product_recovered_no_hdf5_rerun`.
