# Goal 050 Log

## 2026-07-28: Goal opened

Barry approved Goal 050 after Goal 049 separated a passing stable adiabatic
recurrence from a blocked full-loss coefficient/state machine.

The retained local archive contains the 431,744-row adiabatic trace table but
does not contain the time, pressure, density, or adiabatic-index histories
needed to replay equation A11. The immutable completed history cache remains on
Kunanyi at `33191119360` bytes. Goal 050 may therefore use one small remote
post-processing job after the local derivation, tests, and staging gates pass.

The numerical target is the scaled coefficient `lambda = a2 / t1**b`, not raw
dimensional `a2`. This avoids treating a non-representable intermediate as a
scientific failure when the recurrence denominator remains representable.
Physical poles will be classified explicitly and never converted into a
retain-previous-gamma fallback.

No remote command, PBS submission, cache mutation, 4096-row comparison,
raytrace, production run, commit, or push occurred while opening the goal.

## 2026-07-28: local method gate hardened

The stable recurrence and real-panel orchestration were implemented locally.
The first independent scientific audit found one material defect: a formal
antecedent Lorentz factor below one was labelled `subrelativistic` but could
still enter emissivity reconstruction, and no required decision gate rejected
that state.

The repair:

- rejects `subrelativistic` states from emissivity reconstruction;
- requires `no_subrelativistic_states` for a scientific PASS;
- tests both the subrelativistic and explicit `gamma_inf` boundaries; and
- derives `analytic_limits` from executed constant-pressure, removable-limit,
  and overflow-scaled runtime checks rather than a hard-coded Boolean.

Validation after the repair:

- `uv run pytest tests/test_diagnose_g_lo_full_loss_recurrence.py -q`:
  `16 passed`;
- related Goal 048-050 regression suite: `161 passed in 8.61s`;
- `bash -n scripts/kunanyi/g_lo_stable_full_loss_recurrence_gate.pbs`;
- `shellcheck scripts/kunanyi/g_lo_stable_full_loss_recurrence_gate.pbs`; and
- `git diff --check`.

No remote command or PBS submission had occurred at this checkpoint.

## 2026-07-28: audited gate submitted

The closure audit returned GO for only the one-CPU, 64-trace diagnostic. It
independently reproduced the prior adversarial `gamma < 1` case and confirmed
that the repaired decision now fails and emissivity reconstruction raises.
The auditor found no remaining material blocker to this submission.

The live Kunanyi preflight confirmed:

- the Goal 050 stage and analysis paths were unused;
- the immutable cache was readable at `33191119360` bytes;
- the 107-entry staged manifest passed;
- cache, selection, non-finite-record, staged-source, and wrapper hashes passed;
- wrapper syntax, runtime imports, and runtime analytic self-checks passed; and
- `normal` was enabled and started with maximum walltime `48:00:00`.

Exactly one job was submitted through a persistent `qsub_once.lock`:

```text
job_id=779729.kunanyi-ohpc
Job_Name=g_lo_flloss
job_state=Q
queue=normal
qtime=Tue Jul 28 23:09:49 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=64gb
Resource_List.walltime=12:00:00
```

Expected retrieval targets after Barry reports completion:

- archive:
  `/u/bwbrook/codex_kunanyi/goal050_g_lo_stable_full_loss_recurrence_gate/g_lo_stable_full_loss_recurrence_gate_2026-07-28.tar.gz`;
- stdout/stderr under the same stage root; and
- analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-stable-full-loss-recurrence-gate`.

The PBS stop rule was invoked after queued verification. No post-submission
polling, retrieval, 4096-row comparison, raytracing, production, default
change, commit, or push occurred.

## 2026-07-29: stable full-loss gate passed

Barry reported successful completion of PBS `779729.kunanyi-ohpc`. A single
authorized completion check confirmed:

```text
Job_Name = g_lo_flloss
job_state = F
Exit_status = 0
Stageout_status = 1
resources_used.walltime = 00:50:28
resources_used.cput = 02:51:50
resources_used.mem = 949788kb
```

The stage archive, stdout, and empty stderr were retrieved. Remote and local
SHA-256 values agree; the archive SHA-256 is
`fee130640fb1573c82c38b46c6e212def3c1210cb9dd11ad9f9b5e498cf03d01`.

Structured validation found:

- all 11 required gates passed;
- all `431,744` gamma states were finite and reference-classification matched;
- the stable recurrence had zero silent fallbacks and zero subrelativistic
  states;
- raw `a2` failed in exactly `22,737 / 215,872` relevant intervals while the
  scaled coefficient remained finite throughout;
- the pinned `45,474` frequency-specific fallback count reproduced exactly;
- 96 high-precision comparisons had maximum relative difference
  `3.5644138821173953e-13`; and
- all 256 emissivity values were finite and non-negative.

An independent completion audit returned GO for the deterministic 4096-row
comparison only. The real panel contained no physical or `gamma_inf` cutoffs,
so those policies remain supported by reviewed code and synthetic/analytic
tests rather than an observed panel state.

Redundant extracted copies of the large row tables were removed after
validation. The immutable archive and compact decision surfaces remain. No
4096-row comparison, raytrace, production run, default change, commit, or push
occurred.
