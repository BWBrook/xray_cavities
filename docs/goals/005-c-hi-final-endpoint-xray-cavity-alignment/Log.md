# Log: Goal 005 C-HI Final Endpoint X-ray/Cavity Alignment Gate

## 2026-06-11 - X-ray Cavities goal creation

Created by the X-ray Cavities orchestrator after Barry approved the
post-Goal-004 recommendation.

Action repo state before writing this packet:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD da41d13
```

Goal 004 accepted the first full 50 Myr `C-HI` run as a credible prove-out
anchor while identifying the final X-ray path and final cavity protocol as the
largest immediate missing gate. Barry approved proceeding with the proposed
Goal 005 shape: a narrow `C-HI` final endpoint X-ray/cavity alignment gate at
50 Myr, initially `0 deg`, with no new PLUTO production run and no broadening
to `C-LO`, `G-LO`, viewing-angle sampling, source-age sampling, beam/instrument
treatment, or Level 3 ambient-energy method work.

This packet authorizes bounded `kunanyi` post-processing only for the existing
completed 50 Myr `C-HI` endpoint. It does not authorize new production runs,
project-wide interpretation, edits outside the action repo, commits, or pushes.

No project implementation, remote staging, remote job, data workflow, or
validation run was performed by the orchestrator while creating this packet.

## 2026-06-11 - jet start state

Ran the required update/start-state commands before edits:

```text
git fetch --prune origin
git pull --ff-only
Already up to date.

/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 5256de5
```

This differs from the packet's expected `da41d13` because the checkout had
already fast-forwarded to the published Goal 005 packet. The worktree was clean
and even with `origin/main` before Goal 005 edits.

## 2026-06-11 - local design pass

Read the required Goal 005 packet, repo-local orientation docs, Goal 004 audit,
5 Myr XRAiSE/cavity/alignment notes, final quicklook/particle/radio notes, and
the listed XRAiSE, cavity, aligned-comparison, final volume-coupled, and PBS
helpers.

Implementation decision: reuse the existing parameterized grid X-ray extractor
and cavity C extractor for the final endpoint, then add a final-specific local
alignment packager that side-aware joins the new final X-ray/cavity outputs to
accepted Goal 003 Level 1/2 truth and volume-coupled radio scalars. The XRAiSE
source/correction inputs are not tracked in this repo; the final PBS wrapper
therefore verifies and reuses the previously proven remote
`/u/bwbrook/codex_kunanyi/xraise_runtime` inputs before extraction.

Started local implementation only. No remote command, staging, PBS submission,
commit, push, or project broadening occurred in this pass.

## 2026-06-11 - local helper and pre-remote validation

Added:

- `scripts/science/build_final_xray_cavity_alignment.py`
- `tests/test_final_xray_cavity_alignment.py`
- `scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs`

Focused helper validation:

```text
uv run pytest tests/test_final_xray_cavity_alignment.py -q
5 passed in 0.93s
```

Required existing local regression gate:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.85s
```

PBS syntax gate:

```text
bash -n scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs
passed
```

Still no remote command, staging, PBS submission, commit, push, or project
broadening at this point.

## 2026-06-11 - Kunanyi preflight and submission

Initial terminal SSH probe hit the expected TPAC jumpbox window expiry:

```text
MFA check failed. Please login and activate SSH access via the web portal again.
```

Used Chrome only for the TPAC "Enable SSH" selector. The portal reported an
active five-minute SSH window ending at `Thu Jun 11 15:48:13 2026`; then
returned to terminal-first workflows.

Remote read-only preflight confirmed the allowed final endpoint and existing
XRAiSE runtime inputs:

```text
<tpac-host>
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5  44890581676 bytes
/u/bwbrook/codex_kunanyi/xraise_runtime/xraise.py  48561 bytes
/u/bwbrook/codex_kunanyi/xraise_runtime/apec_corrections.txt  1210307 bytes
/u/bwbrook/codex_kunanyi/xraise_runtime/gaunt_lut_2d.npz  725524 bytes
```

Local staged-file hashes:

```text
2a4b2187117b9107d34d28a0c1433645aa70ef375c9ee026a86500b8ffcb1001  scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs
990aa319e87ff5103aa1e8590808c44a26a0ac78135912d8ca0b3c01ed52e59c  scripts/science/xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  scripts/science/pluto_h5_cavity_stub_extract.c
151a6c958e5fa45e710fd2231a9d9915b84344b25514c32ef1ffa1302b1b925b  scripts/science/build_final_xray_cavity_alignment.py
```

Uploaded the PBS wrapper, XRAiSE grid script, and cavity extractor C source to:

```text
/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/
```

Remote hashes matched for the three uploaded files:

```text
2a4b2187117b9107d34d28a0c1433645aa70ef375c9ee026a86500b8ffcb1001  c_hi_final_endpoint_xray_cavity_alignment.pbs
990aa319e87ff5103aa1e8590808c44a26a0ac78135912d8ca0b3c01ed52e59c  xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  pluto_h5_cavity_stub_extract.c
```

Final read-only HDF5/module preflight:

```text
preflight=passed timestep=Timestep_51 shape=(1014, 960, 960) time_code=15330.069689399999
/share/apps/software/HDF5/1.14.0-gompi-2023a/bin/h5pcc
/opt/pbs/bin/qsub
```

Submitted bounded final endpoint post-processing:

```text
qsub c_hi_final_endpoint_xray_cavity_alignment.pbs
697898.kunanyi-ohpc
```

Remote paths:

```text
stage: /u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment
analysis_root: /scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment
archive: /u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/final_endpoint_xray_cavity_alignment_2026-06-11.tar.gz
```

## 2026-06-11 - remote outcome and local package

PBS job `697898.kunanyi-ohpc` ran on `n196` and completed the heavy
post-processing:

- final XRAiSE/GRAiLE grid X-ray extraction wrote finite/nonblank outputs;
- final cavity extraction wrote lobe summaries, projected boundaries, and
  metadata.

The PBS job itself exited `1` after writing products because the wrapper purged
`Anaconda3` for the HDF5 compile/run step and then invoked `python` for
post-cavity validation. On the compute node that resolved to an older
interpreter and failed on an f-string:

```text
SyntaxError: invalid syntax
```

Patched `scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs` to
reload `Anaconda3/2024.02-1` before the post-cavity Python validation and
restaged it to Kunanyi. The corrected wrapper hash is:

```text
2f66acef4dd14ceb98d015491fdd24a00e2f8fdc9a3d1c818eb6f2ad38b71564  c_hi_final_endpoint_xray_cavity_alignment.pbs
```

Ran a lightweight remote finalizer against the already-produced outputs. It did
not rerun the heavy X-ray or cavity extraction. Finalizer result:

```text
finalize_validation=passed
```

Historical PBS status:

```text
job_state = F
resources_used.walltime = 00:21:39
resources_used.cput = 00:12:46
resources_used.mem = 1218084kb
exec_host = n196/1
Exit_status = 1
```

Remote archive created:

```text
/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/final_endpoint_xray_cavity_alignment_2026-06-11.tar.gz
sha256=2d75e982a389ac0db6f9459c14d27ab3c5e749d045da18050f47df544f4c155e
```

Compact local review subset pulled to:

```text
docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/
```

The local subset includes corrected X-ray and tracer maps, axes, X-ray
summary/metadata, cavity summary/boundaries/metadata, remote stdout/stderr, the
alignment scalar tables, metadata, summary, and review figure. The full raw
X-ray and correction-ratio TSV diagnostics remain in the remote archive.

Built the local alignment package:

```text
uv run python scripts/science/build_final_xray_cavity_alignment.py \
  --xraise-dir docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid \
  --cavity-dir docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/cavity_stub \
  --output-dir docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11
```

The helper reported:

```text
gate_status = green
```

Headline scalar results:

```text
corrected_xray_max = 2.874403714611562e6 mJy sr^-1
corrected_xray_sum = 3.212610085481297e9 mJy sr^-1 pixels
cavity_to_level2_volume_ratio negative_z = 1.0000000000032894
cavity_to_level2_volume_ratio positive_z = 1.0000000000021847
cavity_to_level2_volume_ratio bipolar_total = 1.0000000000056688
bipolar four_pV = 2.751221575650812e60 erg
bipolar four_pV / Level 2 tracer-lobe energy = 1.9819430042244381
bipolar four_pV / Level 1 injected energy = 0.8718095088507404
Goal 003 radio comparator = 1.6548347158067362e29 W Hz^-1
```

Added docs:

- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/exchange/logs/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment.md`
- updated `docs/exchange/current_status.md`

No new PLUTO production run, dense all-history particle cache, `C-LO`/`G-LO`,
viewing-angle/source-age sampling, beam/instrument treatment, Level 3
ambient-energy method work, commit, or push occurred.

## 2026-06-11 final validation and closeout

Reran the local Goal 005 validation gate after the final docs, wrapper, helper,
tests, and compact asset package were in place:

```text
uv run pytest tests/test_final_xray_cavity_alignment.py tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
31 passed in 1.71s

bash -n scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs
passed

git diff --check
passed
```

Closeout status: complete for bounded Goal 005 review. The remote PBS job
completed the heavy endpoint extraction but has historical `Exit_status = 1`
because its post-cavity validation picked up an old module-provided Python
after loading HDF5. The wrapper was patched and restaged, and a lightweight
remote finalizer then validated the already-produced outputs and created the
remote archive without rerunning extraction. The local package and science note
therefore carry this caveat explicitly.

## 2026-06-11 review iteration: publishing hygiene, figure polish, finalizer audit trail

Addressed the narrow Goal 005 review items:

- added the Goal 005 fetched asset bundle to `.gitattributes` with `-text -diff`
  to match the Goal 002/003 fetched-review-artifact rules;
- adjusted only the Matplotlib layout/title geometry in
  `scripts/science/build_final_xray_cavity_alignment.py` and regenerated the
  local alignment package/figure from the existing compact local assets;
- added
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/remote_logs/finalizer_validation.txt`
  with a reproducible lightweight finalizer validation transcript and captured
  output for the existing remote archive.

No remote command was rerun for this review iteration. No XRAiSE/cavity
extraction, PBS submission, PLUTO production run, science-default change,
commit, or push occurred.

Fresh focused validation:

```text
uv run pytest tests/test_final_xray_cavity_alignment.py tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
31 passed in 1.69s

bash -n scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs
passed

git diff --check
passed
```

## 2026-06-11 - X-ray Cavities review and acceptance

The X-ray Cavities orchestrator reviewed the Goal 005 helper, tests, PBS
wrapper, science note, exchange log, current-status update, compact asset
bundle, remote logs, finalizer validation transcript, and regenerated review
figure.

Fresh orchestrator validation:

```text
uv run pytest tests/test_final_xray_cavity_alignment.py tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
31 passed in 1.73s

bash -n scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs
passed

git diff --check
passed

uv run python <finalizer transcript marker check>
finalizer_transcript_markers=passed
```

Visual review confirmed that the regenerated
`c_hi_final_endpoint_xray_cavity_alignment.png` no longer has the clipped
top-right title/labels seen in the first Goal 005 review package.

Decision: accepted as a green bounded final 50 Myr `C-HI`, `0 deg`
X-ray/cavity alignment gate. The historical PBS `Exit_status = 1` is accepted
as an audit caveat because the heavy extraction outputs were written, the
failure mode was a post-cavity validation interpreter mismatch, the wrapper was
patched, and the finalizer transcript records reproducible lightweight
validation plus archive SHA evidence for the already-produced outputs.

This acceptance does not make a publication-ready observable claim. Beam or
instrument treatment, Level 3 ambient energy, source-age sampling, additional
views, and `C-LO`/`G-LO` comparison cases remain future gated work.
