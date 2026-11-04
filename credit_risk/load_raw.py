"""Load the downloaded CSV into ``raw.lc_accepted`` as-is, with load metadata.

Every column is kept as text, exactly as in the file, plus ``_source_file``,
``_loaded_at`` and ``_row_hash`` (MD5 of the row). Typing and cleaning happen in
the dbt staging layer.

Usage::

    python -m credit_risk.load_raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from credit_risk.download import FILE
from credit_risk.paths import RAW_DIR, WAREHOUSE


def load_raw(csv_path: Path, warehouse: Path) -> int:
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(warehouse)) as con:
        con.execute("create schema if not exists raw")
        con.execute(
            """
            create or replace table raw.lc_accepted as
            select
                src.*,
                ? as _source_file,
                current_timestamp as _loaded_at,
                md5(src::varchar) as _row_hash
            from read_csv(?, all_varchar = true, header = true) as src
            """,
            [csv_path.name, str(csv_path)],
        )
        return con.execute("select count(*) from raw.lc_accepted").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=RAW_DIR / FILE)
    parser.add_argument("--warehouse", type=Path, default=WAREHOUSE)
    args = parser.parse_args()
    print(f"raw.lc_accepted: {load_raw(args.csv, args.warehouse)} rows")


if __name__ == "__main__":
    main()
