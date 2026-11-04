import re

import duckdb
import pytest

from credit_risk.leakage import (
    DERIVED_SOURCES,
    LeakageError,
    check_features,
    column_policy,
    excluded_columns,
)
from credit_risk.paths import ROOT
from tests.conftest import HEADER

POST_ORIGINATION_EXAMPLES = [
    "total_pymnt",
    "recoveries",
    "last_pymnt_d",
    "last_fico_range_high",
    "out_prncp",
    "debt_settlement_flag",
    "hardship_flag",
    "funded_amnt_inv",
]


def test_policy_covers_every_raw_column_once():
    policy = column_policy()
    assert sorted(policy) == sorted(HEADER)


@pytest.mark.parametrize("col", POST_ORIGINATION_EXAMPLES + ["loan_status"])
def test_known_post_origination_columns_are_excluded(col):
    assert col in excluded_columns()


def test_derived_features_use_application_columns_only():
    policy = column_policy()
    for sources in DERIVED_SOURCES.values():
        assert all(policy[s] == "application" for s in sources)


def test_check_rejects_leaky_and_unknown_columns():
    check_features(["loan_id", "int_rate", "fico_mid"])
    with pytest.raises(LeakageError, match="total_pymnt"):
        check_features(["int_rate", "total_pymnt"])
    with pytest.raises(LeakageError, match="unclassified"):
        check_features(["made_up_column"])


def test_feature_model_reads_only_application_time_models():
    sql = (ROOT / "dbt/models/features/loan_features.sql").read_text()
    assert set(re.findall(r"ref\('(\w+)'\)", sql)) == {"loans", "borrowers"}


def test_built_feature_table_passes_check(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        cols = [r[0] for r in con.execute("describe features.loan_features").fetchall()]
    check_features(cols)


def test_splits_population(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        rows = con.execute(
            """
            select l.term_months, l.issue_year, o.is_resolved, s.split
            from ml.splits s join core.loans l using (loan_id) join core.outcomes o using (loan_id)
            """
        ).fetchall()
    assert rows
    for term, year, resolved, split in rows:
        assert term == 36 and year <= 2015 and resolved
        expected = "train" if year <= 2012 else "validation" if year == 2013 else f"test_{year}"
        assert split == expected
