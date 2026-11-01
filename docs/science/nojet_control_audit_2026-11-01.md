# Retained no-jet controls: signed storage and motion audit

Status: both controls complete; final package and PBS accounting verified.
These are analyses of the retained May-8 simulations, not new PLUTO runs.

## Cluster at 50 Myr

The coarse reflective cluster atmosphere conserves whole-grid mass and total
energy closely but undergoes small local redistribution. The signed total
energy change is +2.74828e53 erg, or 4.36282e-9 of initial whole-grid energy.
That small residual combines thermal -8.15860e55, gravitational +8.15933e55
and kinetic +2.67558e53 erg. Net fractional mass change is -4.02e-19,
at roundoff scale.

Inside 100 kpc, total energy changes by -1.71778e56 erg; outside it changes
by +1.72053e56 erg. The corresponding mass changes are -1.48014e40 and
+1.48014e40 g. Using the explicitly labelled 50-Myr low-power jet comparison
of 3.15576e58 erg, the inner/outer changes are -0.5443%/+0.5452%, whereas the
whole-grid residual is 0.0008709%. No jet energy is assumed injected into
this control. The potential is fixed to the initial atmosphere and zero at
the centre; regional total-energy changes inherit that convention when mass
moves across their boundaries.

The final maximum speed is 1.54821 km/s, Mach 0.00222435, at
(x,y,z)=(-0.5,199.5,0.5) kpc. The velocity is almost purely inward normal to
the +y face, with vy=-1.54820 km/s. This is a cell-centred velocity 0.5 kpc
inside a reflective boundary, not a measurement of mass crossing the wall.
At every saved post-initial time, the speed/Mach maximum lies in an outermost
transverse cell and is already close to its final value at about 10 Myr.
The maximum absolute full-grid density and pressure departures at 50 Myr are
0.008711% and 0.015628%, respectively.

The outermost 1- and 8-cell layers store +3.11325e54 and +2.82132e55 erg
relative to their initial states. These nested regions overlap. Their changes
must not be summed or interpreted as measured boundary fluxes. Whole-grid
conservation can conceal compensating regional changes; nevertheless the
observed departures in this particular setup are small.

## Group and two-atmosphere comparison

The group control is also quiet. Its final thermal change is -7.53308e54 erg,
gravity change +7.53402e54 erg and kinetic change +1.69246e52 erg. The net
+1.78616e52 erg is 4.13645e-9 of its initial whole-grid total energy. Net
fractional mass change is -1.06615e-18, at roundoff scale. Inside/outside
100 kpc the mass changes are -/+2.66958e39 g and the total-energy changes are
-1.24490e55/+1.24669e55 erg.

| Final 50-Myr measure | Cluster | Group |
| --- | ---: | ---: |
| Whole-grid ΔE / initial E | +4.363e-9 | +4.136e-9 |
| Inner 100-kpc ΔE / low-power comparison | -0.5443% | -0.03945% |
| Outer 100-kpc ΔE / low-power comparison | +0.5452% | +0.03951% |
| Maximum 3-D speed | 1.548 km/s | 0.9811 km/s |
| Maximum local Mach number | 0.002224 | 0.002762 |
| Maximum absolute cell density change | 0.008711% | 0.02295% |
| Maximum absolute cell pressure change | 0.01563% | 0.03989% |

The group maximum is at (199.5,-0.5,0.5) kpc, 0.5 kpc inside the +x face,
with vx=-0.98106 km/s: again nearly normal and inward. Both figures show
slices through their own maximum-speed cells, so the cluster and group slices
are at different y coordinates. The colour fields use the full three-component
speed; arrows show only in-plane velocities and have automatic, panel-specific
scaling. Arrow lengths are not a common quantitative scale between figures.

These controls provide no evidence for large spontaneous heating or strong
motions in their own configurations. The small regional changes are real
measured storage differences, but the boundary-associated velocity maxima do
not identify their cause. Their numerical quietness cannot be transferred to
the substantially different production boundary/grid contract. The cost and
sequencing recommendation remains to review the four-case flux and fixed
native-emission pilot before deciding on a new matched control, then prioritize
cluster if the production-background contribution remains material.

## Scope and verification

PBS audit 871750 finished F/0 in 18:49 and passed all 21 tests on Kunanyi.
The final package contains audit outputs derived from all six snapshots per
atmosphere, using their actual saved times rather than assuming exact 10-Myr
spacing. Its 24 members
match the completion receipt exactly by membership, byte count and SHA-256.
The result archive and enclosing seven-member capture match the hashes printed
on Kunanyi; the cluster products are byte-identical to the earlier partial
package. The individual measured peak RSS values were 179,344 KiB (cluster)
and 183,184 KiB (group), with extraction times 573.8 and 515.5 seconds.

Independent combined review passed 12,515 checks with no failures or warnings.
It covers manifests, staged analysis-source hashes,
signed budget algebra, cancellation-aware radial partitions, slice geometry,
zero tracer, and bijective linkage of all 12 source identities to the completed
migration unit and its receipts. The full report is preserved alongside the
checker. The reviewer did not reread or rehash native HDF5 fields. The
historical compiled simulation binary has not been independently reconstructed.
Each atmosphere is represented by one deterministic control run.

The retained controls have reflective boundaries and a uniform 1-kpc grid;
production has outflow boundaries and a stretched grid reaching 0.05 kpc.
Consequently this result does not validate production-background stability,
test production boundary inflow, or justify subtracting these controls from
production. A boundary-associated maximum is a location finding, not causal
identification of the production energy excess.

At 07:23:48 UTC, migration 870323 remained running: nine units complete,
5,696,611,330,969 logical bytes, with exact archive symlinks, live destinations,
receipt hashes and no tombstones. C-LO remains at `copy-start`, with zero file
verification receipts. Flux 870374 and native 871717 remain dependency-held.
No duplicate job or new simulation was submitted.

## Evidence

- `assets/nojet_control_audit_2026-11-01/results_bundle/`: complete original
  two-case package, stage identity, target tests and migration receipts.
- `assets/nojet_control_audit_2026-11-01/independent_review/`: checker and reports.
- `assets/nojet_control_audit_2026-11-01/final_capture/`: final PBS accounting,
  refreshed migration status and verified archive/capture receipts.
- `assets/nojet_control_audit_2026-11-01/cluster_partial_download_receipt.json`:
  local archive hash and per-file preservation hashes.
- `matched_nojet_control_recommendation_2026-11-01.md`: control mismatch,
  compute/storage cost and proposed sequencing.
