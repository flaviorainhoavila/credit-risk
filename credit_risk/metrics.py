"""Discrimination and calibration metrics for a binary default model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


def ks_statistic(y: np.ndarray, p: np.ndarray) -> float:
    """Maximum distance between the score distributions of bads and goods."""
    y = np.asarray(y)
    order = np.argsort(-np.asarray(p), kind="stable")
    ys = y[order]
    ps = np.asarray(p)[order]
    cum_bad = np.cumsum(ys) / ys.sum()
    cum_good = np.cumsum(1 - ys) / (1 - ys).sum()
    # Evaluate only at the last position of each tied score.
    last = np.r_[ps[1:] != ps[:-1], True]
    return float(np.max(np.abs(cum_bad - cum_good)[last]))


def calibration_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Mean predicted and observed bad rate in equal-count bins of the predicted probability."""
    df = pd.DataFrame({"y": y, "p": p})
    df["bin"] = pd.qcut(df["p"].rank(method="first"), n_bins, labels=False)
    out = df.groupby("bin").agg(n=("y", "size"), mean_pd=("p", "mean"), bad_rate=("y", "mean"))
    return [
        {"bin": int(b), "n": int(r.n), "mean_pd": float(r.mean_pd), "bad_rate": float(r.bad_rate)}
        for b, r in out.iterrows()
    ]


def decile_table(y: np.ndarray, p: np.ndarray) -> list[dict]:
    """Deciles by predicted risk, decile 1 the riskiest: bad rate, lift and cumulative capture."""
    df = pd.DataFrame({"y": y, "p": p})
    df["decile"] = 10 - pd.qcut(df["p"].rank(method="first"), 10, labels=False)
    base = df["y"].mean()
    total_bad = df["y"].sum()
    out = df.groupby("decile").agg(n=("y", "size"), bads=("y", "sum")).sort_index()
    out["bad_rate"] = out["bads"] / out["n"]
    out["lift"] = out["bad_rate"] / base
    out["cum_capture"] = out["bads"].cumsum() / total_bad
    return [
        {
            "decile": int(d),
            "n": int(r.n),
            "bad_rate": float(r.bad_rate),
            "lift": float(r.lift),
            "cum_capture": float(r.cum_capture),
        }
        for d, r in out.iterrows()
    ]


def evaluate(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    return {
        "n": int(len(y)),
        "bad_rate": float(y.mean()),
        "mean_pd": float(p.mean()),
        "auc": float(roc_auc_score(y, p)),
        "ks": ks_statistic(y, p),
        "brier": float(brier_score_loss(y, p)),
        "calibration": calibration_table(y, p),
        "deciles": decile_table(y, p),
    }
