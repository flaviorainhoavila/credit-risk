"""Size, bad rate and feature null rates per out-of-time split.

Writes ``results/m2_splits.json``.

Usage::

    python -m credit_risk.split_summary
"""

from __future__ import annotations

import duckdb

from credit_risk.leakage import check_features
from credit_risk.paths import WAREHOUSE
from credit_risk.results import write_result


def main() -> None:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        cols = [r[0] for r in con.execute("describe features.loan_features").fetchall()]
        check_features(cols)
        feats = [c for c in cols if c != "loan_id"]
        splits = [
            dict(
                zip(["split", "first_year", "last_year", "n", "n_bad", "bad_rate"], r, strict=True)
            )
            for r in con.execute(
                """
                select split, min(issue_year), max(issue_year), count(*), sum(is_bad),
                       round(avg(is_bad), 4)
                from ml.splits group by 1 order by 2
                """
            ).fetchall()
        ]
        nulls_sql = ", ".join(f'round(avg(("{c}" is null)::int), 4)' for c in feats)
        null_rows = con.execute(
            f"select split, {nulls_sql} from ml.splits join features.loan_features using (loan_id)"
            " group by 1 order by 1"
        ).fetchall()
    null_rates = {r[0]: dict(zip(feats, r[1:], strict=True)) for r in null_rows}
    path = write_result(
        "m2_splits",
        {"features": feats, "splits": splits, "feature_null_rate_by_split": null_rates},
    )
    print(f"wrote {path}")
    for s in splits:
        print(s)


if __name__ == "__main__":
    main()
