import duckdb

from tests.conftest import STATUSES


def test_raw_keeps_every_line_with_metadata(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        n, hashes, files = con.execute(
            "select count(*), count(distinct _row_hash), any_value(_source_file)"
            " from raw.lc_accepted"
        ).fetchone()
    assert n == 201  # 200 loans plus the footer line
    assert hashes == n
    assert files == "lc.csv"


def test_staging_drops_footer_and_types_columns(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        n = con.execute("select count(*) from staging.stg_lc__loans").fetchone()[0]
        types = {r[0]: r[1] for r in con.execute("describe staging.stg_lc__loans").fetchall()}
    assert n == 200
    assert types["issue_date"] == "DATE"
    assert types["term_months"] == "INTEGER"
    assert types["int_rate"] == "DOUBLE"


def test_label_mapping(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        got = dict(con.execute("select distinct loan_status, is_bad from core.outcomes").fetchall())
    assert got == {
        "Fully Paid": 0,
        "Charged Off": 1,
        "Default": 1,
        "Does not meet the credit policy. Status:Charged Off": 1,
        "Current": None,
        "Late (31-120 days)": None,
    }
    assert set(got) == set(STATUSES)


def test_matured_flag(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        bad = con.execute(
            """
            select count(*) from core.outcomes o join core.loans l using (loan_id)
            where o.is_matured != (date_diff('month', l.issue_date, date '2019-03-31')
                                   >= l.term_months)
            """
        ).fetchone()[0]
    assert bad == 0
