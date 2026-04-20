"""Sensitivity grids, coverage stats, and Mamdani–Sugeno comparison helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fuzzy_engine import FuzzyEngine, INFERENCE_MAMDANI, INFERENCE_SUGENO


def score_grid(
    engine: FuzzyEngine,
    rpm_axis: np.ndarray,
    throttle_axis: np.ndarray,
    egim: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Evaluate the controller on a 2-D grid (len(rpm_axis) x len(throttle_axis)).

    Returns
    -------
    scores : ndarray
        Defuzzified output; NaN where inference failed.
    success_mask : ndarray (bool)
    """
    scores = np.full((len(rpm_axis), len(throttle_axis)), np.nan, dtype=float)
    ok = np.zeros_like(scores, dtype=bool)
    for i, rpm in enumerate(rpm_axis):
        for j, gaz in enumerate(throttle_axis):
            r = engine.evaluate(int(rpm), int(gaz), int(egim))
            if r["success"]:
                scores[i, j] = r["skor"]
                ok[i, j] = True
    return scores, ok


def grid_statistics(success_mask: np.ndarray) -> dict:
    total = success_mask.size
    n_ok = int(np.sum(success_mask))
    return {
        "cells_total": total,
        "cells_success": n_ok,
        "success_rate": float(n_ok / total) if total else 0.0,
        "dead_zone_rate": float(1.0 - (n_ok / total)) if total else 0.0,
    }


def compare_inference_modes(
    config: dict,
    rpm_axis: np.ndarray,
    throttle_axis: np.ndarray,
    egim: float,
) -> tuple[pd.DataFrame, dict]:
    """
    Run Mamdani and zero-order Sugeno on the same grid; return long-form diff table
    and summary statistics.
    """
    m_engine = FuzzyEngine(config, INFERENCE_MAMDANI)
    s_engine = FuzzyEngine(config, INFERENCE_SUGENO)
    m_scores, m_ok = score_grid(m_engine, rpm_axis, throttle_axis, egim)
    s_scores, s_ok = score_grid(s_engine, rpm_axis, throttle_axis, egim)

    rows = []
    for i, rpm in enumerate(rpm_axis):
        for j, gaz in enumerate(throttle_axis):
            if m_ok[i, j] and s_ok[i, j]:
                diff = float(m_scores[i, j] - s_scores[i, j])
                rows.append(
                    {
                        "rpm": int(rpm),
                        "throttle": int(gaz),
                        "egim": int(egim),
                        "mamdani": float(m_scores[i, j]),
                        "sugeno": float(s_scores[i, j]),
                        "abs_diff": abs(diff),
                    }
                )

    df = pd.DataFrame(rows)
    summary = {
        "mean_abs_diff": float(df["abs_diff"].mean()) if len(df) else None,
        "max_abs_diff": float(df["abs_diff"].max()) if len(df) else None,
        "n_comparable": int(len(df)),
        "mamdani_coverage": grid_statistics(m_ok),
        "sugeno_coverage": grid_statistics(s_ok),
    }
    return df, summary


def default_axes(rpm_max: int, rpm_step: int, throttle_step: int) -> tuple[np.ndarray, np.ndarray]:
    rpm_axis = np.arange(0, rpm_max + 1, rpm_step, dtype=int)
    throttle_axis = np.arange(0, 101, throttle_step, dtype=int)
    return rpm_axis, throttle_axis
