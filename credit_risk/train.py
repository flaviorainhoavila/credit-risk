"""Fit the M3 baselines on the training vintages and score every split.

Models: the WoE scorecard (credit_risk.scorecard) and XGBoost with early stopping
on the 2013 validation vintage. Both runs are tracked in MLflow (local file store
in ``mlruns/``). Writes ``ml.scores`` and ``ml.reason_codes`` to the warehouse,
``results/m3_training.json``, ``results/m3_shap.json`` and the SHAP figure.

Usage::

    python -m credit_risk.train
"""

from __future__ import annotations

import pickle

import duckdb
import matplotlib
import mlflow
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from credit_risk.frame import TEST_SPLITS, load_frame
from credit_risk.paths import DATA, ROOT, WAREHOUSE
from credit_risk.results import git_commit, write_result
from credit_risk.scorecard import WoEScorecard

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SEED = 0
TOP_K = 3
SCORECARD_PARAMS = {"n_bins": 10, "min_level_count": 200, "C": 1.0}
XGB_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "tree_method": "hist",
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 50,
    "max_cat_to_onehot": 1,
    "seed": SEED,
}
XGB_ROUNDS = 3000
XGB_EARLY_STOPPING = 100
SHAP_SAMPLE = 20_000
MODELS_DIR = DATA / "models"
FIGURES = ROOT / "figures"
MLRUNS = ROOT / "mlruns"


def xgb_matrix(df: pd.DataFrame, features: list[str], categories: dict) -> pd.DataFrame:
    X = df[features].copy()
    for c, cats in categories.items():
        # Levels not seen in training become missing.
        X[c] = pd.Categorical(X[c].where(X[c].isin(cats)), categories=cats)
    return X


def top_k_reasons(
    contrib: np.ndarray, features: list[str], frame: pd.DataFrame, model: str, k: int = TOP_K
) -> pd.DataFrame:
    """Long table of up to k features that push each applicant toward default.

    Only positive contributions are kept, so a low-risk applicant may have fewer
    than k reasons.
    """
    order = np.argsort(-contrib, axis=1, kind="stable")[:, :k]
    rows = np.repeat(np.arange(len(frame)), k)
    cols = order.ravel()
    values = contrib[rows, cols]
    keep = values > 0
    rows, cols, values = rows[keep], cols[keep], values[keep]
    return pd.DataFrame(
        {
            "loan_id": frame["loan_id"].to_numpy()[rows],
            "model": model,
            "rank": np.tile(np.arange(1, k + 1), len(frame))[keep],
            "feature": np.asarray(features)[cols],
            "contribution": values,
            "feature_value": frame[features].astype(str).to_numpy()[rows, cols],
        }
    )


def fit_scorecard(df, features):
    train = df[df.split == "train"]
    model = WoEScorecard(**SCORECARD_PARAMS).fit(train[features], train.is_bad.to_numpy())
    pd_hat = model.predict_proba(df[features])
    test = df[df.split.isin(TEST_SPLITS)]
    reasons = top_k_reasons(model.contributions(test[features]), features, test, "scorecard")
    info = {"params": SCORECARD_PARAMS}
    return model, pd_hat, reasons, info


def fit_xgboost(df, features):
    categorical = [c for c in features if df[c].dtype == "string"]
    train, valid = df[df.split == "train"], df[df.split == "validation"]
    categories = {c: sorted(train[c].dropna().unique()) for c in categorical}
    dtrain = xgb.DMatrix(
        xgb_matrix(train, features, categories), label=train.is_bad, enable_categorical=True
    )
    dvalid = xgb.DMatrix(
        xgb_matrix(valid, features, categories), label=valid.is_bad, enable_categorical=True
    )
    booster = xgb.train(
        XGB_PARAMS,
        dtrain,
        num_boost_round=XGB_ROUNDS,
        evals=[(dtrain, "train"), (dvalid, "validation")],
        early_stopping_rounds=XGB_EARLY_STOPPING,
        verbose_eval=False,
    )
    best = (0, booster.best_iteration + 1)
    dall = xgb.DMatrix(xgb_matrix(df, features, categories), enable_categorical=True)
    pd_hat = booster.predict(dall, iteration_range=best)

    test = df[df.split.isin(TEST_SPLITS)]
    dtest = xgb.DMatrix(xgb_matrix(test, features, categories), enable_categorical=True)
    # TreeSHAP values in log-odds; the last column is the bias term.
    contrib = booster.predict(dtest, pred_contribs=True, iteration_range=best)[:, :-1]
    reasons = top_k_reasons(contrib, features, test, "xgboost")

    # Global SHAP summary with the shap package on a fixed sample of the 2015 vintage.
    sample = df[df.split == "test_2015"].sample(SHAP_SAMPLE, random_state=SEED)
    Xs = xgb_matrix(sample, features, categories)
    explainer = shap.TreeExplainer(booster)
    sv = explainer(Xs)
    mean_abs = pd.Series(np.abs(sv.values).mean(axis=0), index=features).sort_values(
        ascending=False
    )
    FIGURES.mkdir(exist_ok=True)
    shap.plots.bar(sv, max_display=15, show=False)
    plt.title("XGBoost: mean |SHAP| (log-odds), 20,000 loans from the 2015 vintage")
    plt.tight_layout()
    plt.savefig(FIGURES / "m3_shap_importance.png", dpi=150)
    plt.close("all")

    info = {
        "params": XGB_PARAMS,
        "max_rounds": XGB_ROUNDS,
        "early_stopping_rounds": XGB_EARLY_STOPPING,
        "best_iteration": int(booster.best_iteration),
        "n_trees_used": best[1],
        "categories": {c: list(v) for c, v in categories.items()},
        "shap_mean_abs_test_2015_sample": mean_abs.round(5).to_dict(),
    }
    return booster, pd_hat, reasons, info


def setup_mlflow(experiment: str = "credit-risk-m3") -> None:
    """Local MLflow: SQLite tracking store and artifacts, both under mlruns/ (gitignored)."""
    MLRUNS.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS / 'mlflow.db'}")
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=(MLRUNS / "artifacts").as_uri())
    mlflow.set_experiment(experiment)


def main() -> None:
    df, features = load_frame()
    setup_mlflow()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    scores, reasons, runs = [], [], {}
    for name, fit in [("scorecard", fit_scorecard), ("xgboost", fit_xgboost)]:
        with mlflow.start_run(run_name=name) as run:
            model, pd_hat, why, info = fit(df, features)
            mlflow.set_tags({"git_commit": git_commit(), "seed": SEED})
            mlflow.log_params({k: v for k, v in info["params"].items()})
            mlflow.log_param("features", ",".join(features))
            if "best_iteration" in info:
                mlflow.log_param("best_iteration", info["best_iteration"])
            path = MODELS_DIR / f"{name}.pkl"
            path.write_bytes(pickle.dumps(model))
            mlflow.log_artifact(str(path), artifact_path="model")
            if name == "xgboost":
                mlflow.log_artifact(str(FIGURES / "m3_shap_importance.png"))
            runs[name] = {"mlflow_run_id": run.info.run_id, **info}
        scores.append(
            pd.DataFrame({"loan_id": df.loan_id, "model": name, "split": df.split, "pd": pd_hat})
        )
        reasons.append(why)
        print(f"{name}: fitted, run {run.info.run_id}")

    scores_df = pd.concat(scores, ignore_index=True)
    reasons_df = pd.concat(reasons, ignore_index=True)
    with duckdb.connect(str(WAREHOUSE)) as con:
        con.execute("create schema if not exists ml")
        con.register("scores_df", scores_df)
        con.register("reasons_df", reasons_df)
        con.execute("create or replace table ml.scores as select * from scores_df")
        con.execute("create or replace table ml.reason_codes as select * from reasons_df")

    shap_info = runs["xgboost"].pop("shap_mean_abs_test_2015_sample")
    config = {"seed": SEED, "features": features, "top_k_reasons": TOP_K}
    write_result("m3_training", {"models": runs}, config=config, seed=SEED)
    write_result(
        "m3_shap",
        {
            "model": "xgboost",
            "sample": f"{SHAP_SAMPLE} loans from test_2015",
            "mean_abs_shap": shap_info,
        },
        config=config,
        seed=SEED,
    )


if __name__ == "__main__":
    main()
