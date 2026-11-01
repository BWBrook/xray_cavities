# Retained no-jet controls: signed storage and motion audit

Status: cluster reviewed; group retrieval and final PBS accounting pending.
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

## Scope and verification

PBS audit 871750 passed all 21 tests on Kunanyi. The downloaded cluster
package contains all six snapshot summaries, extrema and the maximum-motion
slice. Independent review passed 6,198 output checks, including manifests,
signed budget algebra, cancellation-aware radial partitions, slice geometry,
zero tracer, and bijective linkage of all six source identities to the
completed migration unit and its receipts. The independent reviewer did not
reread or rehash native HDF5 fields. The historical compiled simulation binary
has not been independently reconstructed.

The retained controls have reflective boundaries and a uniform 1-kpc grid;
production has outflow boundaries and a stretched grid reaching 0.05 kpc.
Consequently this result does not validate production-background stability,
test production boundary inflow, or justify subtracting these controls from
production. A boundary-associated maximum is a location finding, not causal
identification of the production energy excess.

Group results and final audit accounting have not yet been retrieved: the
Mac became locked while using the authenticated Kunanyi portal. The last
observed job state was running. Do not describe the two-case audit as complete.
The recommendation to defer a full matched-control simulation until the
retained flux/native results are interpreted remains unchanged.

## Evidence

- `assets/nojet_control_audit_2026-11-01/cluster_partial/`: original downloaded
  cluster outputs, stage identity, target tests and migration receipts.
- `assets/nojet_control_audit_2026-11-01/independent_review/`: checker and report.
- `assets/nojet_control_audit_2026-11-01/cluster_partial_download_receipt.json`:
  local archive hash and per-file preservation hashes.
- `matched_nojet_control_recommendation_2026-11-01.md`: control mismatch,
  compute/storage cost and proposed sequencing.
