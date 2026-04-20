"""Synthetic driving cycles and batch evaluation for trajectory analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fuzzy_engine import FuzzyEngine


def synthetic_mixed_cycle(n: int = 80, seed: int = 42, rpm_max: int = 7000) -> pd.DataFrame:
    """
    Reproducible pseudo-telemetry: cruise, hill climb, and downhill segment.
    RPM and throttle are clipped to valid universes for the fuzzy controller.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    rpm = 1800 + 18 * t + 120 * np.sin(t / 6) + rng.normal(0, 40, size=n)
    throttle = 35 + 0.45 * t + 8 * np.sin(t / 10) + rng.normal(0, 3, size=n)
    grade = np.zeros(n)
    grade[t < n * 0.35] = 0
    mask_up = (t >= n * 0.35) & (t < n * 0.65)
    grade[mask_up] = 10 + 2 * np.sin(t[mask_up] / 4)
    grade[t >= n * 0.65] = -6

    return pd.DataFrame(
        {
            "step": np.arange(n, dtype=int),
            "rpm": np.clip(rpm, 0, rpm_max).astype(int),
            "throttle": np.clip(throttle, 0, 100).astype(int),
            "grade_deg": np.clip(grade, -20, 20).astype(int),
        }
    )


def evaluate_trajectory(engine: FuzzyEngine, df: pd.DataFrame) -> pd.DataFrame:
    """Append ``skor``, ``tavsiye``, ``success`` from ``FuzzyEngine.evaluate``."""
    scores = []
    tavsiye = []
    success = []
    for _, row in df.iterrows():
        r = engine.evaluate(int(row["rpm"]), int(row["throttle"]), int(row["grade_deg"]))
        scores.append(r.get("skor"))
        tavsiye.append(r.get("tavsiye"))
        success.append(r.get("success"))
    out = df.copy()
    out["skor"] = scores
    out["tavsiye"] = tavsiye
    out["success"] = success
    return out


def trajectory_summary(evaluated: pd.DataFrame) -> dict:
    ok = evaluated["success"].fillna(False)
    return {
        "steps": int(len(evaluated)),
        "success_rate": float(ok.mean()) if len(evaluated) else 0.0,
        "mean_skor": float(evaluated.loc[ok, "skor"].mean()) if ok.any() else None,
        "tavsiye_counts": evaluated.loc[ok, "tavsiye"].value_counts().to_dict() if ok.any() else {},
    }
