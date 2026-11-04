"""Evaluation report per out-of-time vintage: AUC, KS, Brier, calibration, decile lift.

Reads ``ml.scores``; writes ``results/m3_evaluation.json``, figures, and logs the
report to each model's MLflow run.

Usage::

    python -m credit_risk.evaluate
"""

from __future__ import annotations

import json

import duckdb
import matplotlib
import mlflow

from credit_risk.frame import SPLITS
from credit_risk.metrics import evaluate
from credit_risk.paths import RESULTS, WAREHOUSE
from credit_risk.results import write_result
from credit_risk.train import FIGURES, setup_mlflow

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

MODELS = ["scorecard", "xgboost"]


def plot_calibration(report: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True, sharey=True)
    for ax, model in zip(axes, MODELS, strict=True):
        for split in ["validation", "test_2014", "test_2015"]:
            cal = report[model][split]["calibration"]
            ax.plot([c["mean_pd"] for c in cal], [c["bad_rate"] for c in cal], "o-", label=split)
        lim = max(c["bad_rate"] for s in report[model].values() for c in s["calibration"])
        ax.plot([0, lim], [0, lim], "k:", lw=1)
        ax.set_title(model)
        ax.set_xlabel("mean predicted PD (decile of PD)")
    axes[0].set_ylabel("observed bad rate")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "m3_calibration.png", dpi=150)
    plt.close(fig)


def main() -> None:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        df = con.execute(
            "select s.model, s.split, s.pd, l.is_bad from ml.scores s"
            " join ml.splits l using (loan_id)"
        ).df()
        top1 = con.execute(
            """
            select model, feature, count(*) as n,
                   count(*) / sum(count(*)) over (partition by model) as share
            from ml.reason_codes where rank = 1
            group by 1, 2 qualify row_number() over (partition by model order by n desc) <= 5
            order by model, n desc
            """
        ).fetchall()
    reason_top1 = {
        m: [{"feature": f, "n": int(n), "share": float(sh)} for mm, f, n, sh in top1 if mm == m]
        for m in MODELS
    }
    report = {
        model: {
            split: evaluate(g.is_bad.to_numpy(), g.pd.to_numpy())
            for split in SPLITS
            if len(g := df[(df.model == model) & (df.split == split)])
        }
        for model in MODELS
    }
    path = write_result(
        "m3_evaluation",
        {"evaluation": report, "reason_code_rank1_top5_test": reason_top1},
    )
    FIGURES.mkdir(exist_ok=True)
    plot_calibration(report)

    training = json.loads((RESULTS / "m3_training.json").read_text())["models"]
    setup_mlflow()
    for model in MODELS:
        with mlflow.start_run(run_id=training[model]["mlflow_run_id"]):
            for split, m in report[model].items():
                mlflow.log_metrics({f"{split}_{k}": m[k] for k in ("auc", "ks", "brier")})
            mlflow.log_artifact(str(path))
            mlflow.log_artifact(str(FIGURES / "m3_calibration.png"))

    print(f"wrote {path}")
    for model in MODELS:
        for split, m in report[model].items():
            print(
                f"{model:9s} {split:10s} auc={m['auc']:.4f} ks={m['ks']:.4f} brier={m['brier']:.4f}"
            )


if __name__ == "__main__":
    main()
