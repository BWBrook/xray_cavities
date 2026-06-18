# Plan: Goal 009 C-HI Level 3 Remote Extraction Closeout

## Intended Shape

Goal 009 is an execution closeout for Goal 008's tested method:

```text
accepted Goal 008 method package
  + existing baseline/final C-HI HDF5 outputs
  + coordinate-compatible extractor contract
  + reliable access/staging route
  -> bounded remote extraction or queued PBS stop point
  -> compact local thermal/kinetic Level 3 closeout
```

The goal should not redesign the method. The important decision is operational:
can the tested extractor be run and compact outputs retrieved, or is remote
access/staging still the blocker?

## Likely Files

Create:

- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Log.md`

Possibly create:

- `scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/`
- `docs/exchange/logs/2026-06-18-c-hi-level3-remote-extraction-closeout.md`

Possibly modify:

- `scripts/science/pluto_h5_level3_ambient_extract.py`, only for narrow
  operational fixes found while staging/running the accepted extractor;
- `scripts/science/build_final_level3_ambient_energy.py`, only for packaging
  completed extractor CSV rows;
- `tests/test_pluto_h5_level3_ambient_extract.py`;
- `tests/test_final_level3_ambient_energy.py`;
- `docs/exchange/current_status.md`;
- `.gitattributes`, only if a new asset directory needs the usual asset rule;
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Log.md`.

Use a later date suffix if the goal spans more than one day.

## Work Plan

1. Record starting state in `Log.md`.
2. Read the Goal 009 packet and the accepted Goal 008 package.
3. Run the local pre-remote validation gates.
4. Probe the smallest reliable access route:
   - terminal SSH/SCP first if available;
   - Open OnDemand staging/retrieval if terminal access remains blocked and the
     route is reliable enough;
   - stop as `blocked_remote_access` if neither route is reliable.
5. Verify remote baseline/final paths still exist and record the exact command
   or transcript.
6. Choose run mode:
   - if safe and short enough, run bounded extraction directly through the
     reliable route;
   - otherwise stage and submit a PBS post-processing job.
7. If a PBS job is submitted, verify queued/running, wake X-ray Cavities, and
   stop without polling.
8. If compact extractor output is available in this session, retrieve it and
   package local closeout assets.
9. Preserve the gravitational blocker unless reviewed potential/profile
   evidence is available inside authorized repo evidence.
10. Update the science note, exchange log, current status, and `Log.md`.
11. Run final local validation and wake X-ray Cavities.

## Success Criteria

Green closeout requires:

- remote coordinate check executed by the extractor on the baseline/final pair;
- finite thermal and kinetic rows for expected sides;
- no trusted value reported if the coordinate check or required datasets fail;
- comparator ratios included for bipolar thermal, kinetic, and total rows where
  meaningful;
- compact products retrieved locally and checksummed or otherwise auditable;
- focused local validation passes.

Submitted/waiting is also an acceptable intermediate state if:

- the job id is recorded;
- queue or running state is verified;
- stage/output paths are recorded;
- resume instructions are exact;
- `jet` stops without polling.

## Non-Goals

Do not open new simulation work. Do not broaden to additional views, ages, or
cases. Do not revise the enthalpy convention. Do not solve gravitational energy
without a reviewed potential/profile convention. Do not treat login-node
success as permission to run heavy full-grid work there.
