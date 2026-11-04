import numpy as np
import pandas as pd
import pytest
import shap
import xgboost as xgb

from credit_risk.scorecard import MISSING, OTHER, WoEScorecard
from credit_risk.train import top_k_reasons


@pytest.fixture
def toy():
    rng = np.random.default_rng(0)
    n = 4000
    x = rng.normal(size=n)
    cat = rng.choice(["a", "b", "c"], size=n, p=[0.5, 0.45, 0.05])
    logit = -2 + 1.5 * x + np.where(cat == "b", 1.0, 0.0)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    X = pd.DataFrame({"x": x, "cat": pd.Series(cat, dtype="string"), "noise": rng.normal(size=n)})
    X.loc[:50, "x"] = np.nan
    return X, y


def test_scorecard_learns_signal(toy):
    X, y = toy
    sc = WoEScorecard(n_bins=5, min_level_count=300).fit(X, y)
    p = sc.predict_proba(X)
    assert p[X.x > 1].mean() > p[X.x < -1].mean()
    assert sc.bins_["cat"].woe["b"] < sc.bins_["cat"].woe["a"]  # b is riskier
    assert OTHER in sc.bins_["cat"].woe  # "c" has fewer than 300 rows and is pooled
    assert MISSING in sc.bins_["x"].woe


def test_scorecard_contributions_and_points(toy):
    X, y = toy
    sc = WoEScorecard(n_bins=5, min_level_count=300).fit(X, y)
    c = sc.contributions(X)
    assert c.shape == (len(X), 3)
    assert (c >= -1e-12).all()  # measured from each feature's lowest-risk bin
    pts = sc.points(X)
    p = sc.predict_proba(X)
    assert np.corrcoef(pts, p)[0, 1] < -0.9  # more points, lower risk
    unseen = X.head(3).assign(cat=pd.Series(["zzz"] * 3, dtype="string"))
    assert np.isfinite(sc.predict_proba(unseen)).all()


def test_xgboost_contribs_match_shap(toy):
    X, y = toy
    X = X.assign(cat=pd.Categorical(X["cat"]))
    booster = xgb.train(
        {"objective": "binary:logistic", "max_depth": 3, "seed": 0, "tree_method": "hist"},
        xgb.DMatrix(X, label=y, enable_categorical=True),
        num_boost_round=20,
    )
    native = booster.predict(xgb.DMatrix(X, enable_categorical=True), pred_contribs=True)
    sv = shap.TreeExplainer(booster)(X)
    np.testing.assert_allclose(native[:, :-1], sv.values, atol=1e-4)


def test_top_k_reasons_orders_and_drops_negatives():
    contrib = np.array([[0.1, 0.5, -0.2], [-0.1, -0.3, -0.2]])
    frame = pd.DataFrame({"loan_id": [7, 8], "a": [1, 2], "b": [3, 4], "c": [5, 6]})
    out = top_k_reasons(contrib, ["a", "b", "c"], frame, "m", k=3)
    assert out.loan_id.tolist() == [7, 7]
    assert out.feature.tolist() == ["b", "a"]
    assert out["rank"].tolist() == [1, 2]
    assert out.feature_value.tolist() == ["3", "1"]
