"""Fill the README results section from results/*.json.

Everything between the ``<!-- results:start -->`` and ``<!-- results:end -->``
markers is regenerated; nothing in it is written by hand.

Usage::

    python -m credit_risk.report
"""

from __future__ import annotations

import json

from credit_risk.paths import RESULTS, ROOT

README = ROOT / "README.md"
START, END = "<!-- results:start -->", "<!-- results:end -->"
LABELS = {
    "validation": "2013 (validation)",
    "test_2014": "2014 (test)",
    "test_2015": "2015 (test)",
}


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text())


def render() -> str:
    ev = load("m3_evaluation")
    tr = load("m3_training")
    sp = load("m2_splits")
    shap_ = load("m3_shap")
    lines = [
        f"Produced by `{ev['meta']['command']}` at commit `{ev['meta']['git_commit'][:12]}`"
        f" (models from `{tr['meta']['command']}`, seed {tr['meta']['seed']}),"
        f" data SHA-256 `{ev['meta']['data_snapshot'].get('sha256', 'n/a')[:12]}...`."
        " Source: `results/m3_evaluation.json`.",
        "",
        "Out-of-time evaluation by issue year. Both models are fitted on 2007 to 2012;"
        " XGBoost stops early on 2013. Top-decile lift is the bad rate of the riskiest 10%"
        " divided by the vintage bad rate; capture is the share of all bads in the riskiest 30%.",
        "",
        "| Model | Vintage | Loans | Bad rate | Mean PD | AUC | KS | Brier | Top-decile lift"
        " | Capture, top 30% |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model in ["scorecard", "xgboost"]:
        for split, label in LABELS.items():
            m = ev["evaluation"][model][split]
            lines.append(
                f"| {model} | {label} | {m['n']:,} | {m['bad_rate']:.3f} | {m['mean_pd']:.3f}"
                f" | {m['auc']:.3f} | {m['ks']:.3f} | {m['brier']:.4f}"
                f" | {m['deciles'][0]['lift']:.2f} | {m['deciles'][2]['cum_capture']:.3f} |"
            )
    train = next(s for s in sp["splits"] if s["split"] == "train")
    xgb = tr["models"]["xgboost"]
    lines += [
        "",
        f"Training set: {train['n']:,} loans, bad rate {train['bad_rate']:.3f}"
        f" (`results/m2_splits.json`). XGBoost used {xgb['n_trees_used']} trees"
        f" (`results/m3_training.json`). Calibration by PD decile is in"
        " `figures/m3_calibration.png`.",
        "",
        f"XGBoost, top 10 features by mean |SHAP| on {shap_['sample']} (`results/m3_shap.json`):",
        "",
        "| Feature | Mean \\|SHAP\\| (log-odds) |",
        "|---|---|",
    ]
    for feat, v in list(shap_["mean_abs_shap"].items())[:10]:
        lines.append(f"| {feat} | {v:.3f} |")
    lines += [
        "",
        "Most frequent first reason code on the 2014 and 2015 test loans"
        " (`ml.reason_codes`, summarised in `results/m3_evaluation.json`):",
        "",
        "| Model | Feature | Share of loans |",
        "|---|---|---|",
    ]
    for model, rows in ev["reason_code_rank1_top5_test"].items():
        for r in rows[:3]:
            lines.append(f"| {model} | {r['feature']} | {r['share']:.3f} |")
    return "\n".join(lines)


def main() -> None:
    text = README.read_text()
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{render()}\n{END}{tail}")
    print(f"updated {README}")


if __name__ == "__main__":
    main()
