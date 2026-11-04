"""Leakage exclusion list and the check that every model input is application-time.

The classification of every raw column lives in ``dbt/seeds/column_policy.csv``.
Features may use only columns marked ``application``. Derived features must list
their source columns in :data:`DERIVED_SOURCES`.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable

from credit_risk.paths import ROOT

POLICY_FILE = ROOT / "dbt/seeds/column_policy.csv"

DERIVED_SOURCES: dict[str, tuple[str, ...]] = {
    "fico_mid": ("fico_range_low", "fico_range_high"),
    "credit_history_months": ("earliest_cr_line", "issue_d"),
    "loan_to_income": ("loan_amnt", "annual_inc"),
    "payment_to_income": ("installment", "annual_inc"),
    "revol_bal_to_income": ("revol_bal", "annual_inc"),
}

NOT_FEATURES = {"loan_id"}


def column_policy() -> dict[str, str]:
    with POLICY_FILE.open() as f:
        return {row["column_name"]: row["category"] for row in csv.DictReader(f)}


def excluded_columns() -> set[str]:
    """Raw columns that must never feed a model: post-origination, outcome, identifiers."""
    return {c for c, cat in column_policy().items() if cat != "application"}


class LeakageError(ValueError):
    pass


def check_features(columns: Iterable[str]) -> None:
    """Raise LeakageError unless every column traces back to application-time raw columns."""
    policy = column_policy()
    problems = []
    for col in columns:
        if col in NOT_FEATURES:
            continue
        sources = DERIVED_SOURCES.get(col, (col,))
        for src in sources:
            category = policy.get(src)
            if category != "application":
                problems.append(f"{col} (source {src}: {category or 'unclassified'})")
    if problems:
        raise LeakageError("non application-time inputs: " + ", ".join(problems))
