import numpy as np

from diagnostics import compare_inference_modes, default_axes, grid_statistics, score_grid
from engine_configs import ENGINE_CONFIGS
from fuzzy_engine import FuzzyEngine, INFERENCE_MAMDANI


def test_grid_statistics_full_success():
    ok = np.ones((3, 4), dtype=bool)
    s = grid_statistics(ok)
    assert s["success_rate"] == 1.0
    assert s["dead_zone_rate"] == 0.0


def test_score_grid_small():
    cfg = ENGINE_CONFIGS["VW Golf 1.0 TSI (Turbo Benzin)"]
    eng = FuzzyEngine(cfg, INFERENCE_MAMDANI)
    rpm_axis = np.array([2000, 3500])
    thr_axis = np.array([30, 60])
    scores, mask = score_grid(eng, rpm_axis, thr_axis, 0)
    assert scores.shape == (2, 2)
    assert mask.sum() >= 1


def test_compare_modes_runs():
    cfg = ENGINE_CONFIGS["Fiat Linea 1.3 Multijet (Dizel)"]
    rpm_axis, thr_axis = default_axes(cfg["rpm_max"], 400, 25)
    df, summary = compare_inference_modes(cfg, rpm_axis, thr_axis, 0.0)
    assert summary["n_comparable"] >= 1
    assert len(df) == summary["n_comparable"]
