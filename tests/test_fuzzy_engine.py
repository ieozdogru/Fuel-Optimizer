import pytest

from engine_configs import ENGINE_CONFIGS
from fuzzy_engine import FuzzyEngine, INFERENCE_MAMDANI, INFERENCE_SUGENO


@pytest.fixture
def sample_cfg():
    return ENGINE_CONFIGS["Toyota Corolla 1.6 (Benzinli)"]


def test_evaluate_success_shape(sample_cfg):
    eng = FuzzyEngine(sample_cfg, INFERENCE_MAMDANI)
    r = eng.evaluate(2800, 45, 0)
    assert r["success"] is True
    assert "skor" in r and "tavsiye" in r
    assert r["inference"] == INFERENCE_MAMDANI
    assert isinstance(r["rule_firings"], list)
    assert len(r["rule_firings"]) >= 1
    assert all("strength" in row for row in r["rule_firings"])


def test_mamdani_sugeno_finite(sample_cfg):
    m = FuzzyEngine(sample_cfg, INFERENCE_MAMDANI)
    s = FuzzyEngine(sample_cfg, INFERENCE_SUGENO)
    point = (3200, 50, 4)
    rm = m.evaluate(*point)
    rs = s.evaluate(*point)
    assert rm["success"] and rs["success"]
    assert 0 <= float(rm["skor"]) <= 100
    assert 0 <= float(rs["skor"]) <= 100


def test_invalid_inference_raises(sample_cfg):
    with pytest.raises(ValueError):
        FuzzyEngine(sample_cfg, "not-a-mode")
