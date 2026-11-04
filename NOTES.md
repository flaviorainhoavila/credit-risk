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
