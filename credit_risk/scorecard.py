"""Traditional scorecard: weight-of-evidence binning followed by logistic regression.

Numeric features are cut at training-set quantiles, with missing values in their
own bin; categorical features keep levels with enough training rows and pool the
rest. Each bin gets its weight of evidence

    WoE = ln( P(bin | good) / P(bin | bad) ),

with add-0.5 smoothing, and an L2 logistic regression is fitted on the WoE values.
Points follow the usual scaling: ``pdo`` points double the odds of good, and
``base_points`` corresponds to good:bad odds of ``base_odds``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

MISSING = "__missing__"
OTHER = "__other__"


@dataclass
class FeatureBins:
    name: str
    kind: str  # "numeric" or "categorical"
    edges: np.ndarray | None = None
    levels: list[str] = field(default_factory=list)
    woe: dict[str, float] = field(default_factory=dict)

    def labels(self, x: pd.Series) -> pd.Series:
        if self.kind == "numeric":
            idx = np.searchsorted(self.edges, x.to_numpy(dtype=float), side="right")
            lab = pd.Series(idx.astype(str), index=x.index)
            return lab.where(x.notna(), MISSING)
        lab = x.astype("string").fillna(MISSING)
        return lab.where(lab.isin(self.levels) | (lab == MISSING), OTHER).astype(str)

    def transform(self, x: pd.Series) -> np.ndarray:
        # Bins never seen in training (for example a missing value) get WoE 0, i.e. neutral.
        return self.labels(x).map(self.woe).fillna(0.0).to_numpy(dtype=float)


class WoEScorecard:
    def __init__(
        self,
        n_bins: int = 10,
        min_level_count: int = 200,
        C: float = 1.0,
        pdo: float = 20.0,
        base_points: float = 600.0,
        base_odds: float = 50.0,
    ):
        self.n_bins = n_bins
        self.min_level_count = min_level_count
        self.C = C
        self.pdo = pdo
        self.base_points = base_points
        self.base_odds = base_odds

    def _fit_bins(self, x: pd.Series, y: np.ndarray) -> FeatureBins:
        if pd.api.types.is_numeric_dtype(x):
            qs = np.nanquantile(x.to_numpy(dtype=float), np.linspace(0, 1, self.n_bins + 1)[1:-1])
            fb = FeatureBins(x.name, "numeric", edges=np.unique(qs))
        else:
            counts = x.astype("string").value_counts()
            fb = FeatureBins(
                x.name, "categorical", levels=list(counts[counts >= self.min_level_count].index)
            )
        lab = fb.labels(x)
        tab = pd.crosstab(lab, y)
        bad = tab.get(1, 0) + 0.5
        good = tab.get(0, 0) + 0.5
        woe = np.log((good / good.sum()) / (bad / bad.sum()))
        fb.woe = woe.to_dict()
        return fb

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> WoEScorecard:
        y = np.asarray(y, dtype=int)
        self.features_ = list(X.columns)
        self.bins_ = {c: self._fit_bins(X[c], y) for c in self.features_}
        self.model_ = LogisticRegression(C=self.C, max_iter=2000)
        self.model_.fit(self.woe_matrix(X), y)
        return self

    def woe_matrix(self, X: pd.DataFrame) -> np.ndarray:
        return np.column_stack([self.bins_[c].transform(X[c]) for c in self.features_])

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model_.predict_proba(self.woe_matrix(X))[:, 1]

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Per-feature log-odds of bad, relative to the feature's lowest-risk bin.

        Positive values push the applicant toward default; used for reason codes.
        """
        coef = self.model_.coef_[0]
        w = self.woe_matrix(X) * coef
        best = np.array(
            [
                min(v * k for v in self.bins_[c].woe.values())
                for c, k in zip(self.features_, coef, strict=True)
            ]
        )
        return w - best

    def points(self, X: pd.DataFrame) -> np.ndarray:
        """Score in points; higher is lower risk."""
        factor = self.pdo / np.log(2)
        offset = self.base_points - factor * np.log(self.base_odds)
        log_odds_bad = self.model_.decision_function(self.woe_matrix(X))
        return offset - factor * log_odds_bad
