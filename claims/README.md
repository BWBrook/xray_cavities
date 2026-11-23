# Claims ledger

`claims.yaml` is the single source of evidence for everything this project
says in the journal article (`manuscript/text/main.md` and its figure
captions), the two-page brief (`manuscript/text/brief.md`) and the agent guide
(`AGENT_GUIDE.md`). Each product cites claims instead of restating numbers
independently, so drift between them is detectable.

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `ABC-01` form. NAT covers native energetics, BND boundaries and energy balance, OBS observer recovery, DET cavity detection, XR X-ray emission and RAD radio spectra. IDs are permanent. |
| `status` | yes | See below. |
| `statement` | yes | One falsifiable sentence or short paragraph, with its numbers. |
| `evidence` | yes | Paths with the commit at which they hold, checked with `git cat-file`. |
| `reproduce` | when possible | The command that regenerates the evidence, or a pointer to it. |
| `caveats` | no | Scope limits a reader must not miss. |
| `test` | for `open` and `provisional` | What would settle the claim, and how it could fail. |
| `depends_on` | no | Claims this one rests on. |
| `superseded_by` | for `superseded` | The replacing claim. |

## Status

- `supported`: evidence is in the repository and has been checked independently.
- `provisional`: evidence exists, but a named check is pending.
- `open`: a hypothesis with a stated test, not yet resolved.
- `refuted`: tested and failed. Kept permanently; dead ends are evidence.
- `withdrawn`: never tested false, but its basis was invalidated.
- `superseded`: replaced by a better-specified claim.

Claims never leave the ledger. A change of status is a commit with its reason.

## Citing

Put `<!-- claims: NAT-01 DET-03 -->` after the sentence or paragraph that
relies on those claims. The comment does not show in rendered output. The
draft article and brief may cite `supported`, `provisional` and `open` claims.
The submission profile requires `supported` claims. The agent guide may cite
any status so readers can trace an earlier result or a failed method.

Give each figure in the article and brief a standalone claim comment in
the next paragraph. For example,

```markdown
![Enthalpy and regional energy change](../figures/q029_native_energetics.png){#fig-main-1}

<!-- claims: NAT-01 NAT-02 NAT-03 -->
```

## Checking

```bash
.venv/bin/python scripts/claims/check_claims.py
.venv/bin/python scripts/claims/check_claims.py --strict
```

The checker reads the active manuscript sources from both build configurations.
Pandoc identifies figures and claim comments in those sources. The strict
option applies the supported-only rule to each source the submission profile
includes. Both `make manuscript-submission` and `make manuscript-check` run
it before producing submission files. The checker tests citation status and
figure coverage. Scientific review checks that the cited evidence warrants
the wording and plotted quantity.
