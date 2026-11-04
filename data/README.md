# data/

Not committed. Created by `make data`.

- `raw/accepted_2007_to_2018Q4.csv.gz`: Lending Club accepted loans 2007 to 2018Q4, from the Kaggle dataset [wordsforthewise/lending-club](https://www.kaggle.com/datasets/wordsforthewise/lending-club) (Nathan George), listed on Kaggle under CC0: Public Domain. The data was originally published by LendingClub. Downloaded without an API token (Kaggle serves public datasets anonymously).
  - Size: 392,582,231 bytes
  - SHA-256: `55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d`
  - Downloaded 2026-11-04 by `python -m credit_risk.download`, which also writes `raw/manifest.json`.
- `warehouse.duckdb`: DuckDB warehouse (schemas `raw`, `staging`, `core`, `features`, `ml`).
