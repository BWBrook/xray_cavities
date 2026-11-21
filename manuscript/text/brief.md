# Lobe enthalpy is 40–87% of measured jet supply at 30 Myr

Focused native-energy brief · Draft of 21 November 2026\
Barry W. Brook · Calculations and draft by Codex (OpenAI, GPT-6)\
Provisional results from the [X-ray cavities project](https://github.com/BWBrook/xray_cavities).

![Current native 2.5pV divided by cumulative reconstructed gas supply (blue) or labelled kinetic energy (grey), at matched outputs near 30 Myr. Each pair uses the same pressure estimate. Claims NAT-01 and NAT-07.](../../docs/science/assets/native_delivery_restatement_2026-11-21/native_delivery_30myr.png){#fig-native-brief width=100%}

Jets from black holes inflate lobes in the hot gas around galaxies. Their pressure and volume can suggest how much energy the jets supplied. But the answer depends on which gas defines the lobe and what we count as the supplied energy.

Here the *native lobe* means all simulation cells containing more than 0.1% marked jet material, each counted at its full volume. It is a three-dimensional simulation definition, rather than an identified X-ray cavity. We use the usual non-relativistic *enthalpy estimate*, 2.5 times pressure multiplied by volume, as the primary comparison. <!-- claims: NAT-05 NAT-01 -->

We compared four simulations: cluster (C) and group (G) atmospheres, each with high (HI) or low (LO) labelled jet power. We reconstructed energy crossing from the maintained jet injector into freely evolving gas, including pressure work and energy absorbed by the stationary part of the injector. We then added these signed rates over time, using each run's actual saved ages. <!-- claims: NAT-01 -->

1. **The power label understates the reconstructed gas supply.** By 30 Myr the net supply exceeds the labelled kinetic-energy reference by about 16% in C-HI, 11% in C-LO, 16% in G-HI and 15% in G-LO. Dividing by that larger, matched supply lowers the pressure-based fractions shown above. An instantaneous power correction would not give this cumulative comparison. <!-- claims: NAT-01 NAT-07 -->

2. **The four runs retain different pressure-based fractions.** Across the selected ages near 10–50 Myr, 2.5pV accounts for 45–48% of reconstructed supply in C-HI, 58–99% in C-LO, 40–43% in G-HI and 54–68% in G-LO. G-HI contributes only the selected ages through 40 Myr. C-LO's late estimate exceeds its power-label reference but stays below its reconstructed gas supply in all tested methods. Using 4pV instead multiplies every fraction by 1.6; it does not supply a calibrated correction. <!-- claims: NAT-01 -->

3. **Pressure and volume do not measure the same quantity as stored-energy change.** Near 30 Myr the pressure estimate is 43–81% of the change in thermal, motion and gravitational energy inside a surrounding spherical region. The spheres contain the entire native lobe at these ages. Changing the common supply denominator leaves this pressure-to-storage comparison unchanged. It cannot establish that the missing fraction was irreversibly deposited in the atmosphere. <!-- claims: NAT-07 -->

These four runs do not support a universal pressure-to-energy conversion. There is one run per case. The reconstruction misses intermediate solver updates and a short terminal speed dip. The pressure estimate uses current gas, whereas the spherical budget subtracts the initial state and depends on the chosen gravitational reference. These measurements do not establish a closed energy budget or certify the outer simulation boundary. <!-- claims: NAT-01 NAT-07 -->

Separate sums of archived rates and interval balances agree to numerical precision. This new normalization awaits independent review; historical roles remain recorded in the repository.

Sources: claims NAT-01, NAT-05 and NAT-07 in the repository ledger; [matched calculation, tables and sensitivities](https://github.com/BWBrook/xray_cavities/blob/main/docs/science/native_delivery_restatement_2026-11-21.md).
