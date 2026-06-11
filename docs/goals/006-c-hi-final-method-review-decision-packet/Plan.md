# Plan: Goal 006 C-HI Final Method Review Decision Packet

## Intended Shape

Create a decision surface, not a new data product.

```text
accepted Goals 003-005 evidence
  + Honours plan and Meeting 2 requirements
  + agent_comms review history
  -> method-decision matrix
  -> concise science decision note
  -> agent_comms review request
  -> next-goal recommendation
```

The output should make it easy for Stas-agent and Patrick-agent to say
`ACCEPT CURRENT METHOD`, `ACCEPT WITH CHANGES`, or `HOLD`, with evidence-linked
reasons.

## Likely Files

- Create:
  `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- Create:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv`
- Create:
  `docs/exchange/logs/2026-06-11-c-hi-final-method-review-decision-packet.md`
- Create:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- Modify, if useful:
  `agent_comms/requests/open_questions.md`
- Modify, if useful:
  `docs/exchange/current_status.md`
- Modify:
  `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`

Avoid code. A hand-built CSV is acceptable because this is a bounded
decision/evidence synthesis over accepted documents.

## Work Plan

1. Record starting state in `Log.md`.
2. Read the Goal 006 packet and agent-comms protocol.
3. Read the Honours plan, Meeting 2 action plan, relevant agent-comms threads,
   and accepted Goal 003-005 notes/logs.
4. Extract only decision-relevant evidence, especially:
   - Stas-agent's `2.5pV` request;
   - setup-block/reporting requests;
   - cavity age and ambient-shell caveats;
   - Goal 005 scalar outputs and limitations;
   - Honours plan requirements for fixed protocol, viewing angle, source age,
     Level 1/2/3 truth, and comparison cases.
5. Draft the method-decision matrix.
6. Write the science decision note from the matrix.
7. Create the agent-comms thread with a clear current ask and response shape.
8. Update `agent_comms/requests/open_questions.md` if it helps discoverability.
9. Add the exchange log and current-status update if warranted.
10. Update `Log.md`.
11. Run docs/CSV validation gates.
12. Wake X-ray Cavities.

## Expected Recommendation

The likely recommendation is not to broaden immediately to `C-LO`/`G-LO`.

Expected default branch:

- carry `pV`, `2.5pV`, and `4pV` in the next method-facing products;
- treat `2.5pV` as the non-relativistic-plasma interpretation that needs
  Stas review;
- preserve `4pV` as the literature cavity-enthalpy comparator rather than the
  only physical interpretation;
- keep hydrostatic-proxy buoyancy/refill ages labelled provisional;
- ask whether Level 3 ambient energy is a required pre-broadening gate or can
  be a parallel next method goal;
- do one method review before controlled views/source-age sampling or
  comparison-case expansion.

If the evidence points elsewhere, explain why and recommend the better branch.

## Non-Goals

Do not make a supervisor decision on their behalf. Do not run new analysis.
Do not open the next production case. Do not turn this into a manuscript plan.
Do not bury the PBS stop rule; include it as the future remote-work operating
norm for long jobs.
