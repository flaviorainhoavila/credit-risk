import numpy as np
import pytest
from scipy.stats import ks_2samp

from credit_risk.metrics import calibration_table, decile_table, evaluate, ks_statistic


@pytest.fixture
def scored():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.01, 0.6, 20000)
    y = (rng.uniform(size=p.size) < p).astype(int)
    return y, p


def test_ks_matches_scipy(scored):
    y, p = scored
    expected = ks_2samp(p[y == 1], p[y == 0]).statistic
    assert ks_statistic(y, p) == pytest.approx(expected)


def test_ks_handles_ties():
    y = np.array([0, 1, 0, 1])
    p = np.array([0.5, 0.5, 0.5, 0.5])
    assert ks_statistic(y, p) == 0.0


def test_deciles(scored):
    y, p = scored
    d = decile_table(y, p)
    assert [r["decile"] for r in d] == list(range(1, 11))
    assert sum(r["n"] for r in d) == len(y)
    assert d[-1]["cum_capture"] == pytest.approx(1.0)
    assert d[0]["bad_rate"] > d[-1]["bad_rate"]


def test_calibration_of_a_calibrated_model(scored):
    y, p = scored
    for row in calibration_table(y, p):
        assert row["bad_rate"] == pytest.approx(row["mean_pd"], abs=0.05)


def test_evaluate_keys(scored):
    m = evaluate(*scored)
    assert {"auc", "ks", "brier", "calibration", "deciles", "n"} <= set(m)
    assert 0.5 < m["auc"] < 1
