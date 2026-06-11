# Plan: Goal 004 C-HI Final Production Prove-out Gap Audit

## Intended Shape

Produce a decision-quality audit, not another data product.

```text
Meeting 2 / Honours plan gates
  + accepted Goal 001-003 evidence
  + final C-HI endpoint notes
  -> prove-out readiness matrix
  -> corrected current-status next action
  -> recommended Goal 005
```

The audit should leave Barry and the orchestrator with a crisp view of the
first full production run: credible anchor, useful current products, and a
specific list of still-missing gates before wider production or interpretation.

## Likely Files

- Create:
  `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- Create:
  `docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv`
- Create:
  `docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md`
- Modify:
  `docs/exchange/current_status.md`
- Modify:
  `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`

Avoid new code unless it genuinely reduces error in the matrix. A hand-built
CSV is acceptable here because the goal is a bounded evidence audit over
existing documents.

## Work Plan

1. Record starting state in `Log.md`.
2. Read the Goal 004 packet and required project-plan context.
3. Skim Meeting 3 only for whether Meeting 2 remains the active working plan;
   do not turn this into a transcript summary.
4. Read the accepted Goal 001-003 logs and the latest science notes.
5. Draft the status categories, using a small stable set such as:
   - `proven`;
   - `green_narrow`;
   - `proxy_only`;
   - `missing`;
   - `needs_decision`.
6. Build `prove_out_matrix.csv` with one row per prove-out component.
7. Write the audit note from the matrix, with a short narrative synthesis.
8. Update `current_status.md` at the top so the latest next action points to
   the prove-out audit and the next technical gate, not manuscript-facing work.
9. Write the exchange log.
10. Update `Log.md` with evidence read, files changed, validation, and the
    recommended Goal 005 shape.
11. Run the docs/audit validation commands.
12. Wake X-ray Cavities with a concise completion packet.

## Expected Judgement Calls

Be critical. Do not reward a row with `proven` merely because some artefact
exists. The row is proven only if the artefact is aligned with the current full
`C-HI` endpoint and the project-plan gate it claims to satisfy.

Expected classifications:

- Goals 001-003 are green for the sparse selected-ID radio/truth bridge.
- Final endpoint integrity is likely proven as a run-health gate.
- Final quick-look maps are likely proven as health diagnostics, not full
  synthetic-observable products.
- X-ray/cavity final products are likely missing or proxy-only unless existing
  evidence proves otherwise.
- Level 3 ambient-medium energy is likely missing or needs method definition.
- Viewing-angle/source-age sampling is likely missing for the full endpoint.
- Mandatory comparison-suite readiness is not satisfied by the single `C-HI`
  endpoint.

## Non-Goals

Do not launch compute. Do not rewrite the project plan. Do not ask Barry to
approve a major new run as a default next step. Do not frame the output as
manuscript readiness. Do not hide the scale of remaining work.
