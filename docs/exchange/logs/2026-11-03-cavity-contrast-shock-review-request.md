# Handover: cavity contrast and bow-shock review request

Date: 2026-11-03.
Recipients: Barry's agent (`barry-codex`) and Patrick's agent (`patrick-agent`).
Source: supervisor-authorised scientific summary for repository delivery.
Source repository revision: `8f97bb8819d9ffc07bf7c3ed58adb61798b0126b`.

## Request

Separate insufficient line-of-sight X-ray contrast from shocked emission
filling in the projected deficit of tracer-tagged material. Explicitly test
whether the orange deficit arcs coincide with the bow shock or its edges.
The exact questions, motivating G-HI 20-Myr examples, independent shock
overlay, component decomposition and same-cell initial-emissivity replacement
test are in
[the science specification](../../science/xray_cavity_path_length_and_bow_shock_check_2026-11-03.md).
The current-status handover points both recipients to that specification.

## Evidence and limitations

- Refreshed the repository with `git pull --ff-only`; it was up to date.
- Recomputed the four quoted volume/completeness/purity rows from retained
  recovery and native-volume CSVs; both lobes are fully inside the aperture.
- This update changes documentation only. No simulation, native extraction,
  remote analysis job, detector or science claim was changed.
- Bow-shock alignment and shell-filling remain unmeasured in the displayed
  20-Myr example. The existing 40-Myr native pilot is not a substitute.
- Repository delivery does not constitute a private-board post or an
  acknowledgement. Both recipients should pull before acting and report
  results/review through the project's established coordination workflow.
