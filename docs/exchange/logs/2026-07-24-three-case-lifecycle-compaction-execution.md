# 2026-07-24 Three-Case Lifecycle Compaction Execution

Status: `prepared_for_remote_preflight`.

Barry approved exact Goal 046 ledger SHA-256
`df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92`
for permanent deletion of `148` production HDF5 files and their `148` XMF
sidecars. Forecast recovery is `6,845,659,111,424` allocated bytes.

Goal 046 is committed and pushed at `1e9866b`. Goal 047 is a single guarded
execution goal: local implementation, destructive-risk audit, one remote
preflight, one PBS submission, and the normal queued/running stop rule.

The `968` lineage-unproven analysis rows and every other protected or held row
remain outside the authorization. No remote command or mutation has occurred
in Goal 047 at this checkpoint.

The full Goal 046/047 test suite passed with `81 passed, 1 skipped`, and the
final focused Goal 047 suite passed with `42 passed`. Python compilation,
wrapper syntax, all three input manifests, and `git diff --check` passed.
Independent final audit returned `GO`, conditional on a recorded zero-symlink
stage, zero active Barry jobs immediately before submission, and the in-job
self-only qstat gates.

Final audited hashes:

```text
executor=cf93d052e6d4860bb4e598fd84cc28063e615235a09cf96af2e9b1aadce5ae41
wrapper=ffbb9f2fcc96aa5a0075c4aada379de1d9955536471c74f08fb092dafcf3a3e7
```

The remaining operational assumptions are explicitly retained: PBS cannot see
an out-of-band writer, real NFS unlink failure semantics cannot be eliminated
by local tests, and the approved `st_blocks` recovery total may not appear
immediately as an identical quota change.
