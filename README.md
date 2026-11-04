# credit-risk

Consumer credit risk modeling on public data: Lending Club accepted loans (2007 to 2018) loaded into a layered DuckDB warehouse built with dbt, point-in-time features in SQL, and default models evaluated out of time by issue year. This is a rebuild on public data, inspired by past financial-services analytics work. It contains no proprietary code or data.

## Status

M0 (skeleton). Data ingestion, features, models and results are pending.

## Reproduce

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
make setup   # create .venv and install
make test    # pytest
make lint    # ruff
```

## License

MIT, see [LICENSE](LICENSE).
