# Notes

Working log per milestone: what was done, commands, results, open questions.

## M0 Skeleton

Done:

- `pyproject.toml` (hatchling, Python 3.12), flat package `credit_risk/`, `tests/`, `docs/assumptions.md`.
- `Makefile` targets: `setup`, `data`, `build`, `train`, `evaluate`, `report`, `all`, `test`, `lint`. Targets for later milestones exit with an error saying "pending" so that `make all` cannot appear to succeed.
- `.gitignore` excludes `data/` (except `data/README.md`), `mlruns/`, DuckDB files and dbt build output.

Commands:

```bash
make setup && make test && make lint
```

Open questions: none yet.

## M1 Ingestion and warehouse

Source check (2026-11-04):

- Kaggle dataset `wordsforthewise/lending-club`, file `accepted_2007_to_2018Q4.csv.gz`, 392,582,231 bytes, license listed as CC0: Public Domain. The Kaggle API metadata and download endpoints answered without credentials, so no `~/.kaggle/kaggle.json` was needed.
- SHA-256 `55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d` (see `data/README.md`).

Done:

- `credit_risk/download.py`: download, size check, SHA-256, `data/raw/manifest.json`.
- `credit_risk/load_raw.py`: `raw.lc_accepted`, all columns as text plus `_source_file`, `_loaded_at`, `_row_hash`.
- dbt (`dbt/`): `staging.stg_lc__loans` (typed, renamed, footer rows removed; free text and identifiers url, desc, emp_title, title, member_id, zip_code dropped), `core.loans`, `core.borrowers`, `core.outcomes` (status, `is_resolved`, `is_bad`, `is_matured`). Tests: unique, not_null, relationships, accepted_values, and a generic `in_range`.
- `credit_risk/data_quality.py` writes `results/m1_data_quality.json`.
- Tests on a 200-row synthetic file run the real loader and `dbt build` (`tests/conftest.py`).

Commands and results:

```bash
make data    # python -m credit_risk.download; python -m credit_risk.load_raw
make build   # dbt build (4 models, 31 data tests: PASS=35 WARN=0 ERROR=0); python -m credit_risk.data_quality
```

From `results/m1_data_quality.json`:

- Rows: raw 2,260,701; staging and core 2,260,668. The 33 dropped rows are "Total amount funded in policy code ..." summary lines from the concatenated quarterly files (they appear mid-file, not only at the end).
- Duplicates: 0 row hashes, 0 loan ids.
- Sentinels and outliers seen in ranges: `dti` from -1 to 999, `annual_inc` up to 110,000,000, `revol_util` up to 892.3. Handled in the feature layer (M2).
- Several bureau attributes are null for a large share of loans (for example `mths_since_last_delinq` 51%, `mths_since_last_record` 84%); missingness also changes by vintage because Lending Club added fields over time. Checked per vintage in M2.

Decision from the user (2026-11-04): label and maturity choice "36-month loans, matured vintages only" (see `docs/assumptions.md`).

## M2 Features and splits

Done:

- `dbt/seeds/column_policy.csv`: all 151 raw columns classified (103 application, 40 post_origination, 7 identifier_or_text, 1 outcome).
- `features.loan_features` (dbt): one row per loan from `core.loans` and `core.borrowers` only; 32 features including 5 derived (`fico_mid`, `credit_history_months`, `loan_to_income`, `payment_to_income`, `revol_bal_to_income`).
- `ml.splits` (dbt): resolved 36-month loans 2007 to 2015 with `split` in train (2007 to 2012), validation (2013), test_2014, test_2015.
- Leakage guards: `credit_risk/leakage.py` (`check_features`, also called by the training code), `tests/test_leakage.py` (policy covers every raw column; known post-origination columns excluded; the feature model reads only `loans` and `borrowers`; the built table passes the check), and the dbt test `no_leaky_feature_columns` on `loan_features`.
- Label, censoring, maturity and feature choices are in `docs/assumptions.md`.

Commands and results:

```bash
make build   # dbt build: PASS=54 WARN=0 ERROR=0; then data_quality and split_summary
python -m credit_risk.split_summary   # results/m2_splits.json
```

From `results/m2_splits.json`:

| Split | Issue years | Loans | Bad rate |
|---|---|---|---|
| train | 2007 to 2012 | 75,004 | 0.1304 |
| validation | 2013 | 100,422 | 0.1233 |
| test_2014 | 2014 | 162,570 | 0.1373 |
| test_2015 | 2015 | 283,026 | 0.1489 |

Notes:

- The training set is smaller than each later vintage because Lending Club grew quickly. That follows from the out-of-time design chosen with the user.
- `mths_since_last_delinq` is null for 61% of train and 48% of test_2015, so the share of applicants with a past delinquency rises over time.

## M3 Baselines

Done:

- `credit_risk/scorecard.py`: WoE scorecard (10 quantile bins, missing as its own bin, categorical levels with fewer than 200 training rows pooled, L2 logistic regression, points with PDO 20 and 600 at 50:1). Reason contributions are log-odds above each feature's lowest-risk bin.
- XGBoost (`credit_risk/train.py`): depth 4, learning rate 0.05, subsample and colsample 0.8, min_child_weight 50, native categorical handling, early stopping on 2013 (100 rounds). Not tuned.
- SHAP: exact TreeSHAP from `xgboost` `pred_contribs` for the reason codes of all test loans; the `shap` package on a 20,000-loan sample of 2015 for the global summary. A test checks that the two agree.
- `ml.scores` (every split, both models) and `ml.reason_codes` (top 3 positive contributions per test loan) in the warehouse.
- MLflow: local SQLite store and artifacts in `mlruns/`. MLflow 3.18 refuses the plain file store (maintenance mode), so SQLite is used instead; still local only.
- `credit_risk/metrics.py`: AUC, KS, Brier, calibration table and decile lift; `credit_risk/evaluate.py` writes `results/m3_evaluation.json` and logs metrics to the MLflow runs; `credit_risk/report.py` writes the README results section from the JSON files.

Commands:

```bash
make train evaluate report
```

Results: see the README Results section, generated from `results/m3_evaluation.json`, `results/m3_training.json`, `results/m3_shap.json` and `results/m2_splits.json`.

Open questions for review:

- `addr_state` is the first reason code for most test loans under the scorecard, and is high in the XGBoost SHAP ranking. Keep it as a feature, pool it harder, or drop it? Not changed here, to avoid tuning after seeing test results.
- Mean PD is below the observed bad rate in 2015 (vintage drift). Recalibration belongs to M6.
- Random K-fold as a secondary comparison is not run (pending).

## Plan revision (2026-11-08)

No code or results changed. The roadmap now has two parts:

- Part 1, underwriting at origination (Lending Club): M4 lake (Parquet on MinIO) and Dagster; M5 monitoring and Slack; M6 real-time scoring (FastAPI, Feast with Redis, Redpanda, shadow champion/challenger, Kubernetes on kind and one Terraform EKS run); M7 modernization, reject inference with the rejected applications, cutoff and policy analysis, fairness, model card, Tableau Public dashboard.
- Part 2, bust-out detection on a simulated card-issuer consortium (M8 simulator and lake, M9 models with Home Credit as a real-label benchmark, M10 PySpark). Design draft: `docs/design_bust_out.md`.
- The IEEE-CIS fraud module is dropped. Freddie Mac is optional.

Open questions: see the design draft and the M3 questions above (`addr_state`, 2015 calibration).
