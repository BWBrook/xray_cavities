# Three-Case Lifecycle Compaction Execution

## Status

`prepared_for_remote_preflight`

## Approved Scope

Goal 047 executes the exact Goal 046 production deletion ledger approved by
Barry on 2026-07-24:

```text
ledger_sha256=df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
delete_hdf5_rows=148
delete_xmf_rows=148
allocated_bytes=6845659111424
```

This is permanent lifecycle compaction after accepted post-processing and
reduction. It knowingly removes unselected fine-cadence raw trajectory data;
recovery would require rerunning PLUTO.

## Retained Scope

The execution does not include:

- `968` analysis rows held as `HOLD_REGENERATION_UNPROVEN`;
- `5,501` radio-held rows;
- `3` ambiguous symlinks;
- `65` protected rows;
- `10,320` compact provenance rows; or
- any directory, regenerated ledger row, or path outside the frozen allowlist.

## Execution Method

One audited PBS job will validate the complete immutable packet and all
candidate identities/hashes before any mutation. It will hold no-follow file
descriptors through exact path-entry deletion, stop on the first failure, and
record every mutation in a hash-chained fsynced transcript. A full post-scan
must prove that exactly the approved paths disappeared and all retained rows
remained unchanged.

The only material operational assumption is that no out-of-band writer is
modifying Barry-owned roots outside PBS. The job mitigates this with an atomic
lock and two active-job gates, including one immediately before mutation.

## Local Verification And Audit

The full Goal 046/047 suite passed with `81 passed, 1 skipped`; the skip is an
unrelated macOS FIFO-creation limitation. The final focused Goal 047 suite
passed with `42 passed`. Python compilation, PBS syntax, packet and evidence
manifests, the 50-entry staged-input manifest, and `git diff --check` passed.

Independent final audit returned `GO`, conditional on three remote gates:

1. the staged input tree contains zero symlinks;
2. no Barry-owned PBS job is active immediately before `qsub`; and
3. inside PBS, only the Goal 047 job is active at both qstat gates.

Audited code hashes:

```text
executor=cf93d052e6d4860bb4e598fd84cc28063e615235a09cf96af2e9b1aadce5ae41
wrapper=ffbb9f2fcc96aa5a0075c4aada379de1d9955536471c74f08fb092dafcf3a3e7
```

The audit retains three practical residuals: PBS cannot detect an out-of-band
writer, real NFS unlink failure semantics cannot be fully reproduced locally,
and the approved recovery total is the exact sum of frozen `st_blocks` rather
than a guarantee of an immediately identical quota change.
