# 2026-05-12 - C-HI Mini-Production Scheduler Pivot

## Context

The production-scale allocation smoke `690703.kunanyi-ohpc` requested
`80` full `kunanyi` nodes and remained queued for more than a day. Patrick
suggested trying fewer nodes first, and Barry has a meeting with Stas and
Patrick on 2026-05-13 at 13:00 AEST. The practical goal shifted from an
80-node allocation smoke to getting a real reduced-grid `C-HI` continuation
segment running overnight.

## Decision

Cancel the 80-node allocation smoke and submit a meeting-ready
mini-production continuation of the particles-enabled `C-HI` case.

This is still not the final full-grid production suite. It is a scheduler-fit
continuation of the already validated reduced-grid `C-HI` run, using the
production template, HDF5 restart path, and Patrick's `-maxtime` guard.

## Queue Ladder

The following shapes were tried in order:

| PBS job | Shape | Ranks | Outcome |
| --- | ---: | ---: | --- |
| `690703.kunanyi-ohpc` | `80 x 28` | `2240` | cancelled after >1 day queued |
| `691414.kunanyi-ohpc` | `25 x 28` | `700` | cancelled; insufficient CPU resources |
| `691416.kunanyi-ohpc` | `23 x 28` | `644` | cancelled; insufficient CPU resources |
| `691417.kunanyi-ohpc` | `25 x 20` | `500` | cancelled; insufficient CPU resources |
| `691418.kunanyi-ohpc` | `16 x 28` | `448` | cancelled; insufficient CPU resources |
| `691422.kunanyi-ohpc` | `8 x 28` | `224` | running |

The partial-node test used:

```text
select=25:ncpus=20:mpiprocs=20
```

The rationale was that PLUTO mostly needs MPI ranks, and the production
template derives rank count from `PBS_NODEFILE`. In practice PBS still rejected
that request under the current scheduler state, so the live job reverted to
full-node allocation but at `8` nodes.

## Live Job

```text
PBS job: 691422.kunanyi-ohpc
Name: c_hi_8mini
Queue: normal
Request: select=8:ncpus=28:mpiprocs=28
Ranks: 224
Walltime: 15:00:00
PLUTO maxtime: 14.5 h
Email: barry.brook@utas.edu.au, begin/abort/end
```

The first running-state poll reported:

```text
Tue May 12 20:34:03 AEST 2026
job_state = R
resources_used.walltime = 00:02:31
exec_host = n169/0*28+n180/0*28+n212/0*28+n216/0*28+n064/0*28+n063/0*28+n072/0*28+n135/0*28
```

A second poll confirmed it was still running:

```text
Tue May 12 20:39:41 AEST 2026
job_state = R
resources_used.walltime = 00:07:21
resources_used.ncpus = 224
resources_used.mem = 5392872kb
```

At that point the PLUTO log existed and only showed first-contact SSH host-key
warnings from OpenMPI startup across the allocated nodes, not a PLUTO failure.

The job uses the standard production template copied to:

```text
/u/bwbrook/codex_kunanyi/jet_setup_production_template_latest.pbs
```

The local wrapper is:

```text
scripts/kunanyi/c_hi_8node_mini_production.pbs
```

## Expected Restart

The template has `RESTART_POLICY=auto`, so it should select the latest available
restart-capable `dbl.h5` output from:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem/outputs/dbl.h5.out
```

At the last documented checkpoint this was expected to be `-h5restart 7`, the
walltime-stop checkpoint at about `10.278 Myr`.

## Follow-Up When PBS Email Lands

1. Re-open or enable the jumpbox SSH window.
2. Poll/fetch `691422.kunanyi-ohpc`.
3. Check the PLUTO log for `RUN_KIND`, final time, and clean `-maxtime`
   shutdown.
4. Harvest compact outputs and update the through-time diagnostics.
5. Prepare the meeting summary from the new segment if it completed cleanly.
