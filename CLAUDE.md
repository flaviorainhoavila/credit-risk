# credit-risk: consumer credit risk modeling with a real data platform underneath

## Purpose

A portfolio rebuild, on public data, of a production-style consumer credit risk system: out-of-time validation, gradient boosting, SHAP explanations and reason codes, then a modernization pass (alternative models, calibration, leakage audit, monitoring, drift, alerting). The point is as much the data engineering as the model: raw files to a layered warehouse queryable with SQL, tested and orchestrated, with Slack alerts.

Context for the author's background and honesty rules is in `../CLAUDE.md` and `../PROJECTS.md` (local only, not in this repo). Read them first. The README must describe this as a rebuild on public data inspired by past financial-services work, with no proprietary code or data.

## Ground rules

1. No number in README, notes or commit messages unless produced by a script in this repo, with the command next to it. Not run means "pending".
2. Fixed seeds; every result written to `results/*.json` with seed, git commit, data snapshot and config.
3. **Out-of-time validation is the primary evaluation.** Random K-fold only as a secondary, clearly labeled comparison.
4. Leakage discipline: features may only use information available at decision time (loan issue / application date). Post-origination fields (payments, recoveries, last payment date, final status details) are excluded from features, and a test enforces the exclusion list.
5. Small, verifiable steps. Update `NOTES.md` after each milestone: what was done, commands, results, open questions. Stop after each milestone for review unless the user said to continue.
6. Every commit passes `pytest` and `ruff`. No data files in git (`data/` gitignored); tests use tiny synthetic fixtures.
7. Plain, concise English. No em dashes. No marketing language.

## Data

- **Primary (day one): Lending Club accepted loans, 2007 to 2018** (about 2 million loans, with issue date, so out-of-time splits by issue year are natural). Commonly mirrored on Kaggle (for example `wordsforthewise/lending-club`). Verify the source, size and license before downloading; if the Kaggle CLI needs credentials (`~/.kaggle/kaggle.json`) and they are missing, stop and ask the user. Record the exact source and checksum in `data/README` and NOTES.md.
- **Scale-up (later milestone): Freddie Mac Single-Family Loan-Level Dataset** (origination plus monthly performance files across many vintages; tens of GB). Requires free registration by the user. This is where PySpark is justified.
- **Fraud module (later): IEEE-CIS Fraud Detection** (Kaggle competition; transaction and identity tables). Requires accepting competition rules.
- Target for Lending Club: default = loan_status in {Charged Off, Default} (and the "Does not meet the credit policy" variants mapped accordingly); exclude loans still Current / In Grace / Late at snapshot time from training labels, or treat as censored, and document the choice in `docs/assumptions.md`. Note the maturity bias for recent vintages (36 vs 60 month terms) and handle it explicitly (e.g. restrict evaluation vintages to those with matured outcomes, or use a fixed performance window).

## Stack

Python 3.12, pyproject (hatchling), pytest, ruff. DuckDB as the day-one warehouse; dbt (dbt-duckdb) for SQL transformations and tests; XGBoost, LightGBM, scikit-learn, SHAP; MLflow (local file store) for experiment tracking. Later: Postgres via Docker Compose, PySpark, Dagster (preferred) or Airflow, Slack alerting. A `Makefile` with targets: `data`, `build` (dbt), `train`, `evaluate`, `report`, `all`, `test`, `lint`.

## Warehouse layout (dbt)

- `raw`: loaded as-is, typed minimally, with load metadata (source file, load time, row hash).
- `staging`: cleaned, typed, renamed, one model per source entity.
- `core`: normalized entities, for example `borrowers` (anonymous profile at application), `loans` (terms, grade, issue date), `outcomes` (final status, label, observation window), and `loan_snapshots` if monthly data exists. Primary and foreign keys with dbt tests (unique, not_null, relationships, accepted_values).
- `features`: one row per loan, point-in-time correct, built in SQL where reasonable.
- `ml`: train / validation / out-of-time test splits by issue date, scores, reason codes, monitoring tables (PSI per feature per vintage, score distribution, performance by vintage), and later `alerts`.

## Modeling

- Baseline: logistic regression with WoE / binned features (the traditional scorecard) and XGBoost. Report AUC, KS, Brier, calibration curve, and lift / capture rate by decile, per out-of-time vintage.
- Explainability: SHAP global and local; top-k reason codes per applicant stored in a table.
- Modernization pass (later milestone): LightGBM / CatBoost, monotonic constraints where business logic implies them, probability calibration (isotonic / Platt), leakage audit, fairness check on available proxies with a clear limitations note, stability over vintages (PSI), and a model card.

## Milestones

- **M0 Skeleton**: repo, pyproject, Makefile, ruff, pytest, .gitignore, README stub, NOTES.md, docs/assumptions.md, git init.
- **M1 Ingestion and warehouse**: download script with checksum, raw load into DuckDB, dbt staging and core models with tests, a data-quality summary (row counts, nulls, ranges, duplicates) written to results.
- **M2 Features and splits**: point-in-time feature model in SQL, leakage exclusion list with a test, out-of-time splits by issue year.
- **M3 Baselines**: scorecard-style logistic regression and XGBoost, MLflow tracking, SHAP, reason-code table, evaluation report per vintage. README results table filled from results/*.json.
- **M4 Orchestration and data-quality gates**: Dagster assets for the pipeline; failing dbt tests stop the run.
- **M5 Monitoring and Slack alerting**: PSI and score drift by vintage, performance decay, alerts table, webhook alerts (level 1), then a Bolt app with buttons and `/pipeline status` (level 2). Webhook mocked in tests.
- **M6 Modernization**: alternative models, calibration, monotonic constraints, model card.
- **M7 Scale-up**: Freddie Mac with PySpark into the same layered layout; compare runtimes.
- **M8 Fraud module**: IEEE-CIS, class imbalance, precision at fixed alert budget, time-based split.

**Today's target: M0 through M3**, pushed to GitHub with a README that a reviewer can run end to end (`make all`) and whose results table comes from the scripts. If time is short, stop at a clean, honest M2 and mark M3 as pending.

## README requirements

- One-paragraph summary: what problem, what data, what was built.
- Architecture diagram (Mermaid) of the layers and pipeline.
- How to reproduce (exact commands; data download prerequisites).
- Results table (out-of-time, per vintage) from results/*.json only, with the command that produced it.
- Limitations (public data, censoring and maturity choices, no proprietary elements).
- Roadmap (M4 to M8).
- Dataset citations and licenses.
