# Native enthalpy with a matched injector denominator

Primary numerator: current `2.5*sum(p_i V_i)` over the whole native binary lobe (`tr1 > 1e-3`), from the reviewed turn-15 exact-native-volume tables. It is absolute current pressure energy, without initial subtraction. The historical Q029 numerator is carried as a separately labelled historical numerator cross-check.

Primary denominator: cumulative signed **gas-energy** flux from the maintained injector to freely evolved cells, cone plus stationary-region contributions, integrated from the already initialized t=0 output to the exact same case and output age. Gas energy includes internal and kinetic energy and pressure work in its flux; this denominator does not add gravitational-potential transport. The primary reconstruction is `linear_snapshot_flags` and the primary time rule is trapezoidal. Left/right rectangles, first-order states and forced-HLL/HLLC are separate sensitivities. These are saved-state estimates, not recovered Runge–Kutta-stage injection counters.

The labelled comparator remains bipolar kinetic power times actual active age, capped at the configured 50 Myr. It is never renamed realised delivery. The selected surface is indices 10/20/30/40/50 in C-HI/C-LO/G-LO and 10/20/30/40 in G-HI, with actual ages matched exactly. G-HI 48–50 are not extrapolated or used.

A second diagnostic divides R100 current-minus-t=0 stored thermal+kinetic+fixed-potential energy by the same gas-delivery denominator. This is signed storage within a changing aperture and retains potential-zero and geometry qualifications. Its agreement or disagreement with unity is not physical closure. The ratio of native 2.5pV to R100 storage is unaffected by changing a common external denominator.

Allowed: report the fraction of reconstructed cumulative net injector gas energy represented by current native 2.5pV, with matched case, age, lobe/volume definition and quadrature. Keep 2.5pV primary; 4pV is a factor-1.6 comparator.

Not allowed: call labelled kinetic supply measured delivery; use a pilot interval or an instantaneous power factor as a universal cumulative correction; equate current pV with same-cell stored-energy change; interpret R100 normalization as a closure test; infer the source of the exterior residual; extend the injector estimate beyond the retained G-HI history; treat four unreplicated cases as a population calibration.

Startup transients, the unsaved terminal velocity dip and missing intermediate solver states limit the time integral. Negative stationary-region flux is included with its sign, because it absorbs gas energy. Tracer-mass closure diagnoses time-resolution problems but does not bound gas-energy error. Any brief or paper statement using the new denominator must name it as a reconstructed cumulative quantity.

## Paired restarts and subsequent production histories, 23 November

For comparisons of lobe growth after the shared restart, divide the change in $2.5\int p\,dV$ in each arm by the net gas energy delivered in that arm over the same interval. For the thermal and kinetic response through time, use ergs or a fixed energy scale to quantify growth. Normalising by the increasing input since the common seed answers a different question.

The production exterior residual integrates signed storage, outer transport and net injector transport, including potential flux and the maintained-cell stock. BND-14 and BND-15 directly measure the entropy update during 10–12 Myr. BND-16 describes the residual history at other ages on the calibrated reconstruction. A late counterfactual lobe enthalpy or wave flux requires information beyond that residual. [Regional identity and calibration](../production_entropy_review_2026-11-23/README.md)
