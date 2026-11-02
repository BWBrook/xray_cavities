# Claims ledger

`claims.yaml` is the single source of evidence for everything this project
says: the journal article (`manuscript/text/main.md`), the two-page brief
(`manuscript/text/brief.md`, not yet started) and the agent guide
(`AGENT_GUIDE.md`). Each product cites claims instead of restating numbers
independently, so drift between them is detectable.

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `ABC-01` form. The prefix names the topic: NAT native energetics, BND boundaries and closure, OBS observer recovery, DET cavity detection, XR emission. IDs are permanent and never reused. |
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
article and brief may cite only `supported`, `provisional` and `open` claims.
The agent guide may cite any claim.

## Checking

```bash
uv run python scripts/claims/check_claims.py
```

`tests/test_claims_ledger.py` runs the same check in the test suite.
