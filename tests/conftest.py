"""Tiny synthetic Lending Club file and a warehouse built from it by the real pipeline."""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from credit_risk.load_raw import load_raw

ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "tests/fixtures/lc_header.csv").read_text().strip().split(",")
STATUSES = [
    "Fully Paid",
    "Charged Off",
    "Current",
    "Late (31-120 days)",
    "Default",
    "Does not meet the credit policy. Status:Charged Off",
]
GRADES = list("ABCDEFG")


def synthetic_rows(n: int = 200, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows = []
    for i in range(n):
        year = int(rng.integers(2008, 2016))
        row = dict.fromkeys(HEADER, "")
        row.update(
            id=str(1000 + i),
            loan_amnt=str(int(rng.integers(1000, 35000))),
            term=" 36 months" if rng.random() < 0.8 else " 60 months",
            int_rate=f"{rng.uniform(5, 25):.2f}",
            installment=f"{rng.uniform(30, 1200):.2f}",
            grade=GRADES[int(rng.integers(0, 7))],
            sub_grade="A1",
            emp_length="10+ years",
            home_ownership="RENT",
            annual_inc=str(int(rng.integers(20000, 200000))),
            verification_status="Verified",
            issue_d=f"{months[int(rng.integers(0, 12))]}-{year}",
            loan_status=STATUSES[i % len(STATUSES)],
            purpose="credit_card",
            addr_state="CA",
            dti=f"{rng.uniform(0, 40):.2f}",
            earliest_cr_line=f"Mar-{year - int(rng.integers(3, 30))}",
            fico_range_low=str(int(rng.integers(660, 800))),
            revol_util=f"{rng.uniform(0, 100):.1f}",
            application_type="Individual",
            last_pymnt_d="Feb-2019",
            total_pymnt=f"{rng.uniform(0, 40000):.2f}",
        )
        row["fico_range_high"] = str(int(row["fico_range_low"]) + 4)
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict]) -> Path:
    # The real file is a concatenation of quarterly files; each part ends with summary
    # lines ("Total amount funded in policy code ...") padded with empty fields.
    footer = dict.fromkeys(HEADER, "") | {"id": "Total amount funded in policy code 1: 123"}
    half = len(rows) // 2
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows[:half] + [footer] + rows[half:])
    return path


@pytest.fixture(scope="session")
def fixture_csv(tmp_path_factory) -> Path:
    return write_csv(tmp_path_factory.mktemp("raw") / "lc.csv", synthetic_rows())


@pytest.fixture(scope="session")
def warehouse(tmp_path_factory, fixture_csv) -> Path:
    """Warehouse built by load_raw and `dbt build` (models and dbt tests) on the fixture."""
    path = tmp_path_factory.mktemp("wh") / "warehouse.duckdb"
    load_raw(fixture_csv, path)
    env = {**os.environ, "CREDIT_RISK_WAREHOUSE": str(path)}
    target = tmp_path_factory.mktemp("dbt_target")
    proc = subprocess.run(
        [
            str(ROOT / ".venv/bin/dbt"),
            "build",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--target-path",
            str(target),
            "--log-path",
            str(target),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout[-3000:]
    return path
