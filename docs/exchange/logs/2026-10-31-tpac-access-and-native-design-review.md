# TPAC access diagnosis and native design review

Barry asked Codex to resolve Claude's SSH difficulty and read the new Board
reply. Discussion 29 message 2712 contains Claude's scientific review;
responses 2714–2716 contain the access diagnosis, table measurements and design
adjudication. No SSH configuration, credentials, key authorization or network
policy was changed. No native extraction job was submitted.

## Mini access: password authentication, not a rejected key

Live `ssh -G` and `~/.ssh/config` agree that both
`tpac-jumpbox-via-nectar` and `kunanyi-via-nectar` explicitly set
`PubkeyAuthentication no` and `PreferredAuthentications password`. This matches
`~/work/nectar/docs/machines/kunanyi.md`. The route is mini → Nectar → TPAC
jumpbox → Kunanyi; the existing old `nectar-codex` spelling resolves to Nectar.

One read-only verbose BatchMode probe reached authentication at
`<tpac-jumpbox>` as `bwbrook`. The server offered `publickey,password`;
the client then reported no usable authentication methods and permission denied.
No password was supplied and no public key authentication was attempted on that
hop. The method names in the error are the server's advertised alternatives,
not evidence that a particular key was offered and rejected. Transport reached
the jumpbox; successful password login and the final Kunanyi hop were not tested.

Codex's successful remote work uses the authenticated Chrome Open OnDemand
portal and its Clusters → Shell Access shell on `kunanyi-00`. This does not
demonstrate passwordless SSH from mini. Claude was told to use that browser
route where its harness supports it. For terminal access, Barry can enable the
portal SSH window and start ordinary interactive `ssh kunanyi-via-nectar`,
entering TPAC credentials at the prompts. BatchMode suppresses the required
password interaction. Opening the jumpbox window does not provision a key.

## Actual interpolation-table ranges

The existing portal shell read these two files with NumPy and hashed their
bytes in `/u/bwbrook/codex_kunanyi/xraise_runtime`:

| File | Coordinate | Minimum | Maximum |
| --- | --- | ---: | ---: |
| `apec_corrections.txt` | T, keV | 0.01 | 10 |
| same | redshift | 0.01 | 10 |
| `gaunt_lut_2d.npz` | T, K | 100000 | 10000000000000 |
| same | f, Hz | 1e16 | 1e19 |

SHA-256 values match the frozen selected-age PBS expectations:

- APEC: `e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3`
- Gaunt: `64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747`

`xraise_grid_smoke.py` uses temperature in keV/redshift for APEC and temperature
in K/frequency in Hz for Gaunt. Both interpolators use linear extrapolation;
`nan_to_num` preserves finite negative corrected emissivities. The selected-age
job uses redshift 0.05. These checks establish the table domains and renderer
convention; no native out-of-range fractions were measured here.

## Scientific response

The revised `docs/science/q031_native_path_length_design_2026-10-31.md` accepts
the initial-state-through-current-masks decomposition and table-coverage audit.
Independent review adds case-specific nozzle-initialized baselines, signed
brightness/mass changes, explicit ratio denominators and area weights, and
removes an unjustified no-jet bound. Tracer-support equality is tested rather
than assumed; half-plane revolution estimates expose geometric asymmetry.

C-HI and G-HI at 40 Myr are the fixed pilot, selected from the existing Q-029
quantitative-bilateral closeout before reading the new retained detector
outputs. The source manifest rows will be bound at staging. Implementation,
native allocation, detector adoption and topology changes are not completed
by this design review. Existing jobs were not modified or re-launched.
