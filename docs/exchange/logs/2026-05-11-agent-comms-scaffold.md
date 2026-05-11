# Agent Communications Scaffold

Date: 2026-05-11

## Summary

Created a repo-mediated asynchronous communication layer under:

```text
agent_comms/
```

Purpose: allow Barry's, Stas', and Patrick's Codex agents to exchange
questions, review requests, result summaries, and decision candidates through
ordinary GitHub pull/edit/commit/push workflows.

This is a practical workaround for the current lack of direct Codex
agent-to-agent communication in this project workflow.

## Structure Added

```text
agent_comms/
  README.md
  AGENTS.md
  agents/
  decisions/
  requests/
  results/
  templates/
  threads/
```

Initial active threads:

- `agent_comms/threads/2026-05-11-onboarding-and-current-state.md`
- `agent_comms/threads/2026-05-11-production-scale-allocation.md`
- `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`

Initial open request queue:

- `agent_comms/requests/open_questions.md`

## Collaboration Norms

The scaffold asks agents to:

- pull before writing
- use append-only thread updates
- include `From`, `To`, `Status`, and `Commit` metadata
- link to canonical artifacts rather than copying them
- avoid secrets and large outputs
- promote settled decisions back to canonical docs or scripts

## First Review Requests

Patrick's agent is asked to review:

- the 80-node allocation smoke
- PLUTO/HDF5/restart details before production-rank startup tests
- particle/radio diagnostics before production

Stas' agent is asked to review:

- through-10-Myr `C-HI` interpretation
- whether shakedown results justify moving toward production-scale preparation
- which scalar trends matter most for the honours narrative

## Follow-Up

When Stas' and Patrick's agents are active, they should:

1. read `agent_comms/README.md`
2. fill in or revise their profile under `agent_comms/agents/`
3. respond to the active threads
4. update `agent_comms/requests/open_questions.md` when questions are answered
