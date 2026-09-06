# Q-029 accepted; Q-030 first Results and figures ready

Barry supplied the completion notification for PBS `790871.kunanyi-ohpc`.
Scheduler history confirmed `F/0`, walltime 02:40:26, CPU time 04:27:01 and
peak memory 41,205,920 KB. Retrieved the approximately 226 KiB compact archive,
verified its checksum, and accepted all four worker exits and 51 runtime tests.
Local validation reproduced the 228 native-row/census comparison and all 19
precision records. Component partition residuals are at most 2.30e-14 of
injected energy; threshold-rounding enthalpy sensitivity is below 2.58e-7.

The refreshed shock surface retains 15/19 quantitative ages and the same four
late C-LO failures. Native enthalpy remains a conditional energy proxy, and
X-ray geometry/topology dominates recovery discrepancies. C-LO's median
X-ray/native enthalpy ratio changes from 6.76 to 0.494. A focused independent
review accepted the interpretation after three repairs: jointly scaled shock
threshold wording, explicit non-spatial ambient-allocation ratio naming, and
replacement of stale Goal 065 power numerators with the accepted X-ray
pressures. All 74 cavity-side geometries agree exactly; ages and censoring
remain unchanged. Four new power tests and 10 closeout tests passed.

The first Methods/Results/Discussion iteration and three figures are now in
`manuscript/`. The corrected power factorisation uses an enthalpy-weighted
harmonic effective age for side-based clocks. Fractional-field spectral ages
remain explicitly labelled. Native-resolution no-jet subtraction, boundary
flux, causal coupling efficiency and population inference remain outside scope.

Configuration validation, manuscript/citation lint and submission-profile
checks passed. Draft and submission PDF/DOCX files were rendered; draft
captions and figures were inspected. Both profiles use a caption page followed
by figure pages to avoid duplicate labels in the external engine's inline mode.
The PDF/DOCX are first-iteration review documents with remaining scaffold
sections, not a submission-ready paper.

Accepted analysis and provenance:
`docs/science/q029_binary_native_refresh_2026-09-06.md` and its asset directory.
Review PDF: `build/manuscript/draft/xray_cavities_draft.pdf`.
No further compute or independent audit is needed for this tranche. Q-029 is
analytically complete; the first Q-030 iteration awaits supervisor feedback.
No commit, push, external collaborator message or new remote job was made.
