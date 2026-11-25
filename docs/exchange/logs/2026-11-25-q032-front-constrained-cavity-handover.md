# Patrick's Q-032 review: constrain cavity candidates by the compression front

The magenta outline looks like a credible trace of the compressive front in the G-HI example at 20 Myr. That is not a confirmed shock identification. The broad outer orange arcs look like a background-fitting artefact rather than the front or the lobes. Refitting shrinks the exterior arc, but the remaining arc is still nearly circular. Better agreement in inferred volume is not enough to show that the cavity was recovered correctly.

1. **Test the front constraint in the simulation.** In the 0, 45 and 90 degree side-on views, compare the existing deficit candidates with the same candidates restricted to the interior of the independently mapped compression front. Keep the background fit fixed to isolate the effect of the constraint. Use the native tracer outline to report false exterior area removed and true lobe area lost, by view and lobe. Flag ambiguous or open fronts rather than forcing an enclosing boundary.
2. **Use that result to develop an observer-only method.** If the constraint reduces false detections without losing substantial real lobe area, test whether an outer boundary estimated from X-ray brightness edges alone can do the same. Use it to limit where cavities can be selected, not as the cavity wall or proof of a shock. Test on held-out views, including cases without a reliable edge. Keep this separate from the existing DET-05 scores.

Evidence: `docs/science/ghi20_compressive_front_comparison_2026-11-23.md` and `docs/exchange/logs/2026-11-23-ghi20-compressive-front-method-review.md` in `xray_cavities`.

From: Patrick. To: Barry's agent and collaborators. This is a Git handover, not a live board message or authorization for a new simulation.
