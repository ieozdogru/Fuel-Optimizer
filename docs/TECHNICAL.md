# Technical note: inference and diagnostics

## Inputs and output

The controller uses three antecedents on discrete universes built at runtime:

- Engine speed (RPM), scaled per vehicle profile (`rpm_max`, `ideal_range`, `high_rev`).
- Throttle (0–100%).
- Road grade (−20° to +20°).

The consequent is a scalar **assistant score** on [0, 100], mapped to four advisory classes (shift down, lift throttle, hold, shift up) by maximum membership at the defuzzified value (same interpretation layer for both inference modes).

## Mamdani (scikit-fuzzy)

Rules follow the usual Mamdani pipeline: antecedent aggregation (min), activation of consequent fuzzy sets, accumulation (max), then **centroid** defuzzification via `scikit-fuzzy`.

Rule firing strengths exposed in the UI correspond to `aggregate_firing` on the simulation object after `compute()`.

## Zero-order Sugeno (implemented)

Many `scikit-fuzzy` builds only support centroid-like modes in `defuzz()`, not library `wtaver` for this path. For portability, **Sugeno mode** uses the same rule base but:

1. Computes each rule’s antecedent satisfaction with the same min semantics as the fuzzy AND tree.
2. Maps each rule’s consequent linguistic term to a **singleton** real value.
3. Aggregates with the standard zero-order Sugeno crisp output:  
   \( y = \frac{\sum_i w_i \, s_i}{\sum_i w_i} \)  
   where \(w_i\) is rule \(i\) firing strength and \(s_i\) its singleton.

This is comparable to Mamdani on identical IF parts while changing **only** the THEN aggregation, which is a standard experiment in fuzzy control coursework.

## Diagnostics

The diagnostics tab evaluates the controller on a coarse RPM × throttle grid at a fixed grade. The **dead-zone rate** is the fraction of cells where Mamdani inference fails (no aggregated output membership), which highlights sparse rule coverage.

## Trajectory tab

A synthetic cycle varies RPM, throttle, and grade. Fuzzy (Mamdani) scores are plotted alongside a **crisp baseline** from `baselines.py` to report agreement rate—a simple “non-fuzzy comparator” metric for reports.
