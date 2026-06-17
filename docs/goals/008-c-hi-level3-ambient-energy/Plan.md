# Plan: Goal 008 C-HI Level 3 Ambient Energy Method Gate

## Intended Shape

Produce a bounded post-processing method gate, not a new simulation:

```text
Stas Q-013 says Level 3 is required before broadening
  + Patrick Q-015 clears X-ray product readability
  + final C-HI endpoint HDF5
  + validated Level 1/2 truth products
  -> baseline-relative ambient energy method
  -> thermal / kinetic / gravitational component table
  -> comparison against Level 1, Level 2, 2.5pV, 4pV
  -> reviewed pre-broadening status
```

The output should make it obvious whether Level 3 is now green for `C-HI`
endpoint review, partial with a named gravitational blocker, or blocked by
missing baseline/field inputs.

## Likely Files

- Create:
  `scripts/science/build_final_level3_ambient_energy.py`
- Possibly create or modify:
  `scripts/science/pluto_h5_level3_ambient_extract.c`
- Possibly create:
  `scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs`
- Create:
  `tests/test_final_level3_ambient_energy.py`
- Create:
  `docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md`
- Create:
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/`
- Create:
  `docs/exchange/logs/2026-06-17-c-hi-final-level3-ambient-energy.md`
- Modify, if useful:
  `docs/exchange/current_status.md`
- Modify:
  `docs/goals/008-c-hi-level3-ambient-energy/Log.md`

Use a later date suffix if the goal spans more than one day.

## Work Plan

1. Record starting state in `Log.md`.
2. Read Goal 008 packet and required context.
3. Inspect existing Level 1/2 truth products and HDF5 truth extractor.
4. Identify final and baseline/reference HDF5 inputs.
5. Decide the first Level 3 mask/reference convention from available evidence.
6. Write focused tests for:
   - component-status handling;
   - baseline/final compatibility checks;
   - ambient tracer mask logic;
   - ratio calculations against Level 1, Level 2, `2.5pV`, and `4pV`;
   - blocked gravitational component representation.
7. Implement or adapt local packaging helpers.
8. If needed, create a bounded Kunanyi post-processing wrapper for existing
   outputs only.
9. Run local validation.
10. Run or stage bounded remote post-processing only if required and within
    the Goal 008 boundary.
11. Package compact Level 3 artefacts locally.
12. Write the science note, exchange log, and current-status update.
13. Finish `Log.md`.
14. Run final validation and wake X-ray Cavities.

## Expected Recommendation

The likely successful outcome is one of two branches:

- `green_for_c_hi_endpoint_review`: thermal, kinetic, and gravitational ambient
  components are computed against a valid baseline and compared with Level 1,
  Level 2, `2.5pV`, and `4pV`.
- `partial_green_with_gravitational_blocker`: thermal and kinetic ambient
  components are computed, while gravitational energy is blocked by a missing
  potential/profile/convention that is named precisely.

Either branch is useful. The first may allow a pre-broadening method review.
The second should drive a very narrow follow-up method/input goal, not a new
simulation.

## Non-Goals

Do not open new production simulation work. Do not broaden to new views, ages,
or cases. Do not treat sparse radio maps as final observables. Do not make the
Level 3 method a universal default for all future cases unless the evidence
supports that review-level claim.
