"""Data-quality summary of the warehouse: row counts, nulls, ranges, duplicates.

Writes ``results/m1_data_quality.json``.

Usage::

    python -m credit_risk.data_quality
"""

from __future__ import annotations

import duckdb

from credit_risk.paths import WAREHOUSE
from credit_risk.results import write_result

NUMERIC_TYPES = {"DOUBLE", "INTEGER", "BIGINT", "DATE"}


def column_profile(con: duckdb.DuckDBPyConnection, table: str) -> dict:
    cols = con.execute(f"describe {table}").fetchall()
    n = con.execute(f"select count(*) from {table}").fetchone()[0]
    profile = {}
    for name, dtype, *_ in cols:
        if name.startswith("_"):
            continue
        q = f'select count(*) - count("{name}")'
        if dtype in NUMERIC_TYPES:
            q += f', min("{name}"), max("{name}")'
        row = con.execute(f"{q} from {table}").fetchone()
        entry = {"type": dtype, "null_fraction": round(row[0] / n, 6)}
        if dtype in NUMERIC_TYPES:
            entry["min"], entry["max"] = row[1], row[2]
        profile[name] = entry
    return profile


def summarize(con: duckdb.DuckDBPyConnection) -> dict:
    one = lambda q: con.execute(q).fetchone()[0]  # noqa: E731
    counts = {
        t: one(f"select count(*) from {t}")
        for t in [
            "raw.lc_accepted",
            "staging.stg_lc__loans",
            "core.loans",
            "core.borrowers",
            "core.outcomes",
        ]
    }
    duplicates = {
        "raw_row_hash": one("select count(*) - count(distinct _row_hash) from raw.lc_accepted"),
        "staging_loan_id": one(
            "select count(*) - count(distinct loan_id) from staging.stg_lc__loans"
        ),
    }
    status = dict(
        con.execute(
            "select loan_status, count(*) from core.outcomes group by 1 order by 2 desc"
        ).fetchall()
    )
    by_vintage = [
        dict(
            zip(
                ["issue_year", "term_months", "n", "resolved_fraction", "bad_rate_resolved"],
                r,
                strict=True,
            )
        )
        for r in con.execute(
            """
            select issue_year, term_months, count(*),
                   round(avg(o.is_resolved::int), 4),
                   round(avg(o.is_bad), 4)
            from core.loans l join core.outcomes o using (loan_id)
            group by 1, 2 order by 1, 2
            """
        ).fetchall()
    ]
    return {
        "row_counts": counts,
        "rows_dropped_in_staging": counts["raw.lc_accepted"] - counts["staging.stg_lc__loans"],
        "duplicates": duplicates,
        "loan_status_counts": status,
        "by_vintage": by_vintage,
        "columns": {
            "core.loans": column_profile(con, "core.loans"),
            "core.borrowers": column_profile(con, "core.borrowers"),
            "core.outcomes": column_profile(con, "core.outcomes"),
        },
    }


def main() -> None:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        payload = summarize(con)
    path = write_result("m1_data_quality", payload)
    print(f"wrote {path}")
    print("row counts:", payload["row_counts"])
    print("duplicates:", payload["duplicates"])


if __name__ == "__main__":
    main()
