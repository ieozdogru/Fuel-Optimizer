"""Simple non-fuzzy baselines for academic comparison (same numeric inputs)."""

from __future__ import annotations


def crisp_recommend(
    rpm: int,
    throttle: int,
    grade_deg: int,
    *,
    ideal_min: int,
    ideal_max: int,
    high_rev: int,
) -> dict:
    """
    Heuristic thresholds: no fuzzy overlap, useful as a naive comparator.

    Returns keys aligned with ``FuzzyEngine.evaluate`` for UI reuse.
    """
    tavsiye = "DURUMU KORU"
    skor = 55.0

    if grade_deg <= -3 and ideal_min <= rpm <= ideal_max + 400:
        tavsiye = "GAZDAN ÇEK"
        skor = 35.0
    elif rpm > high_rev and throttle >= 25 and grade_deg >= -2:
        tavsiye = "VİTES BÜYÜT"
        skor = 78.0
    elif rpm < ideal_min - 150 or (grade_deg >= 6 and rpm < ideal_max):
        if throttle >= 35 or grade_deg >= 8:
            tavsiye = "VİTES KÜÇÜLT"
            skor = 18.0
    elif rpm > high_rev + 200:
        tavsiye = "VİTES BÜYÜT"
        skor = 80.0

    return {
        "skor": skor,
        "tavsiye": tavsiye,
        "success": True,
        "inference": "crisp_baseline",
        "defuzz_method": "n/a",
        "antecedent_mu": [],
        "rule_firings": [],
    }
