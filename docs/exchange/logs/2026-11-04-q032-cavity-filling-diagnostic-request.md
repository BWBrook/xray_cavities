# Q-032: cavity filling and environment diagnostics

Date: 2026-11-04T03:32:27Z.
From: Patrick, conveyed by `patrick-agent`.
To: Barry's agent (`barry-codex`) and the Q-032 cavity-recovery lead/reviewers.
Status: human-approved request for repository delivery; response pending.
Source repository revision: `57ed770` (request documentation uncommitted at drafting).

## Addition to the open question

To add to Stas's comments on the X-ray cavity finding:

1. Please quantify what fraction of the X-ray cavity is actually filled.
   State what "filled" means and distinguish material/volume filling from
   X-ray emission filling in the projected deficit, so these are not conflated.
2. Separate the cavity from its surrounding environment and produce diagnostic
   plots of both, showing which material contributes to the X-ray morphology.
3. Could a velocity cut help identify the cavity? Please investigate its
   usefulness and limitations alongside the tracer and shock diagnostics,
   rather than assuming a particular cut or definition in advance.

Please respond within the existing Q-032 investigation, explaining the adopted
definitions, showing the diagnostic plots and reporting the measured fractions
and any limitations. These are questions for investigation, not approval of an
algorithm change or a particular velocity threshold. Reuse the existing-output
scope and coordination gates; no new PLUTO simulation is requested.

## Context and delivery

- [Stas's cavity-contrast and bow-shock request](2026-11-03-cavity-contrast-shock-review-request.md).
- [Existing diagnostic specification](../../science/xray_cavity_path_length_and_bow_shock_check_2026-11-03.md).
- [Q-032 discussion context](../../correspondence/thread-0029.md).

This request is delivered through the Git repository at Patrick's direction.
The public correspondence snapshot was exported on 4 November at 02:20 UTC,
through message 2874 in discussion 29. It is not edited to simulate a post.
Repository delivery does not establish a live-board message ID or recipient
acknowledgement. No code, detector, simulation or scientific result is changed.
