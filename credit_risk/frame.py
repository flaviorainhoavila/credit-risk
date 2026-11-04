"""Modeling frame: features joined to the out-of-time splits."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from credit_risk.leakage import check_features
from credit_risk.paths import WAREHOUSE

SPLITS = ["train", "validation", "test_2014", "test_2015"]
TEST_SPLITS = ["test_2014", "test_2015"]
ID_COLUMNS = ["loan_id", "issue_year", "split", "is_bad"]


def load_frame(warehouse: Path = WAREHOUSE) -> tuple[pd.DataFrame, list[str]]:
    """Return the modeling frame and the feature names, after the leakage check."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        df = con.execute(
            """
            select s.loan_id, s.issue_year, s.split, s.is_bad, f.* exclude (loan_id)
            from ml.splits s join features.loan_features f using (loan_id)
            order by s.loan_id
            """
        ).df()
    features = [c for c in df.columns if c not in ID_COLUMNS]
    check_features(features)
    categorical = [c for c in features if not pd.api.types.is_numeric_dtype(df[c])]
    for c in categorical:
        df[c] = df[c].astype("string")
    return df, features
