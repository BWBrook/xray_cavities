# Handover Note: 2026-04-24 macbook-trip-handoff

## Session Context

- Machine used: WSL control plane
- Operator path: `/home/bwbrook/papers/xray_cavities`
- `xray_cavities` commit before this handoff: `0ed2279`
- Relevant UTAS AGN branch context from `AGENTS.md`:
  - `pluto`: `bwbrook/deep-server-bringup`
  - `jet-setup`: `bwbrook/deep-server-bringup`
  - `plutokore`: `bwbrook/deep-server-bringup`

## What Was Done

- created a detailed MacBook-oriented handover at
  `docs/READ_THIS_FIRST.md`
- summarized the project goals, completed onboarding and planning work, current
  six-week accelerated timeline, and next research tasks
- documented the relationship between the pilot-first plan and Stas and
  Patrick's 11-step workflow
- recorded the key simulation, observable, and truth-energy definitions that
  should carry forward during the trip
- added a return-handoff convention for the MacBook agent to use before work
  moves back to WSL

## Files / Workspaces Touched

Local repo files:

- `docs/READ_THIS_FIRST.md`
- `docs/exchange/current_status.md`
- `docs/exchange/logs/2026-04-24-macbook-trip-handoff.md`

No PLUTO, `jet-setup`, or `plutokore` source files were changed in this handoff.

## Validation

- checked the new handover for non-ASCII characters
- ran `git diff --check`
- confirmed the repo was otherwise clean apart from the intentionally untracked
  external feedback note:
  `docs/feedback_on_draft_hons_research_plan.md`

## Current State

- project planning and meeting-prep materials are complete
- the real research phase has not yet begun
- the next scientific step is to process supervisor feedback and lock the Week 2
  pilot simulation specification
- the MacBook should treat `docs/READ_THIS_FIRST.md` as the primary handover
  note after cloning or pulling from GitHub

## Next Recommended Step

1. On the MacBook, clone or pull `xray_cavities`.
2. Read `AGENTS.md` and `docs/READ_THIS_FIRST.md`.
3. Record the outcomes of the supervisor meeting.
4. Convert those outcomes into a concrete Week 2 execution plan.

## Sync Notes

- This handoff should be committed and pushed to GitHub before the trip.
- The MacBook does not need the WSL-only `/mnt/c/Temp/` PDF exports to continue;
  the committed Markdown and QMD sources are sufficient.
- If substantial work happens on the MacBook, create a return note under
  `docs/exchange/logs/` before moving back to WSL.

## Blockers / Risks

- MacBook access to the UTAS AGN GitLab repos and remote execution machines is
  not yet verified in this handoff.
- The external feedback file remains untracked on WSL by design and should not
  be assumed available on the MacBook.
- Heavy simulation work may be better driven through Nectar or `deep-server`
  rather than run locally on the MacBook.

