# 2026-06-18 C-HI Level 3 Remote Extraction Closeout

## Context

Goal 009 was opened to run the accepted Goal 008 Level 3 thermal/kinetic
ambient-energy extractor on the existing final 50 Myr `C-HI` baseline/final
HDF5 pair, or reach a precise submitted/waiting/blocker state.

The scientific contract carried forward from Goal 008 is that matching HDF5
field shapes are not enough: the extractor must compare baseline/final `X`,
`Y`, and `Z` coordinate axes before cell-wise subtraction. No thermal or
kinetic value should be trusted unless that coordinate check executes on the
full remote pair.

## Local Prep

Added a bounded PBS wrapper:

```text
scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs
```

It uses only the accepted existing inputs:

```text
baseline:
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0

final:
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Intended stage and output roots:

```text
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy
```

The wrapper requests one normal PBS node for bounded post-processing only:

```text
select=1:ncpus=1:mpiprocs=1:mem=64gb
walltime=04:00:00
```

## Access And Submission Result

Pre-remote local tests passed, but terminal SSH failed:

```text
ssh -o BatchMode=yes -o ConnectTimeout=12 kunanyi-via-deep hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).
Connection closed by UNKNOWN port 65535

ssh -o BatchMode=yes -o ConnectTimeout=12 kunanyi-via-nectar hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).
Connection closed by UNKNOWN port 65535
```

The operational correction from X-ray Cavities clarified that raw
`BatchMode=yes` is not decisive for the password-auth jumpbox route. After the
Open OnDemand 5-minute selector was refreshed through Chrome / `@chrome`, the
repo-local secret-safe expect helper worked:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd'
<tpac-host>
/u/bwbrook
```

Staged files under:

```text
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/
```

Remote SHA-256 matched local:

```text
00d4f10b729cd74982514f4dde52c8ef7f5ee7a2b1074305d479c99aa6cd26de  pluto_h5_level3_ambient_extract.py
3e84ff8a27571d1dac66b958390a97d924d17b9694262788380b98b66c8fdc97  c_hi_final_level3_ambient_energy.pbs
```

Remote wrapper syntax check passed:

```text
bash -n c_hi_final_level3_ambient_energy.pbs
<no output>
```

Submitted from the remote stage directory:

```text
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

The PBS stop rule was invoked. No polling was done after queue verification.

Expected remote products:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy/level3_extractor_output.csv
/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy/remote_logs/
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/final_level3_ambient_energy_2026-06-18.tar.gz
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/c_hi_final_level3_ambient_energy.out
/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy/c_hi_final_level3_ambient_energy.err
```

## Completion Retrieval

Barry reported the PBS completion email for `699326.kunanyi-ohpc`, and X-ray
Cavities refreshed the Chrome/Open OnDemand jumpbox window. Resumed through the
repo-local password-auth helper.

Remote job status:

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
Exit_status = 0
```

Retrieved compact outputs to:

```text
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/
```

Key local files:

```text
level3_extractor_output.csv
level3_ambient_energy.csv
level3_method_decisions.csv
level3_metadata.json
remote_logs/c_hi_final_level3_ambient_energy.out
remote_logs/c_hi_final_level3_ambient_energy.err
remote_logs/final_level3_ambient_energy_2026-06-18.tar.gz
```

Remote stdout reported:

```text
baseline_hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960)
final_hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960)
level3_extractor_validation=passed
```

Remote stderr is zero bytes. The retrieved archive checksum is:

```text
77d01152913072afcfcf4a0ebffdb9d50a50afea8a25ddb9c311e04cb8cd1d96
```

Thermal/kinetic result status:

```text
green_level3_thermal_kinetic_closeout
```

Overall status:

```text
partial_green_with_gravitational_blocker
```

Headline bipolar values:

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

The coordinate-compatibility contract executed inside the remote extractor:
the SHA-matched extractor compares baseline/final `X`, `Y`, and `Z` axes with
`rtol=0` and `atol=1e-10 kpc` before streaming field subtraction, and the
remote job reached `level3_extractor_validation=passed`.

## Validation

```text
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
..............                                                           [100%]
14 passed in 0.19s

bash -n scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs
<no output>

git diff --check
<no output>
```

## Next Step

Review the Goal 009 closeout package as a thermal/kinetic Level 3 method
result for the accepted final `C-HI` endpoint. Keep gravitational Level 3
blocked unless a reviewed potential/profile convention is provided. The next
project decision is whether this is sufficient to open a controlled broadening
goal or whether Stas/Patrick want gravitational Level 3 resolved first.
