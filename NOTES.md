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
