{#-
  One row per loan, point-in-time correct: built only from core.loans and
  core.borrowers, which hold what was known at application or issue. Nothing
  here reads core.outcomes or a post-origination column; tests/test_leakage.py
  and the dbt test no_leaky_feature_columns enforce this.

  ASSUMPTION: only attributes populated in every vintage used for modeling
  (2007 to 2015) are kept. About 30 bureau attributes (tot_cur_bal, bc_util,
  mort_acc, ...) are empty for all loans issued before 2012 and for about half
  of 2012, so they would be absent in training and present in test.
-#}

with l as (select * from {{ ref('loans') }}),
     b as (select * from {{ ref('borrowers') }})

select
    l.loan_id,

    -- loan terms and Lending Club pricing at issue
    l.loan_amnt,
    l.int_rate,
    l.installment,
    l.grade,
    l.sub_grade,
    l.purpose,
    l.verification_status,

    -- borrower, self-reported
    b.emp_length,
    b.home_ownership,
    b.annual_inc,
    -- dti of -1 and 999 are sentinels in the source file
    case when b.dti >= 0 and b.dti < 999 then b.dti end as dti,
    b.addr_state,

    -- credit bureau at application
    (b.fico_range_low + b.fico_range_high) / 2 as fico_mid,
    date_diff('month', b.earliest_cr_line_date, l.issue_date) as credit_history_months,
    b.delinq_2yrs,
    b.inq_last_6mths,
    b.mths_since_last_delinq,
    b.mths_since_last_record,
    b.open_acc,
    b.total_acc,
    b.pub_rec,
    b.pub_rec_bankruptcies,
    b.tax_liens,
    b.revol_bal,
    b.revol_util,
    b.collections_12_mths_ex_med,
    b.acc_now_delinq,
    b.chargeoff_within_12_mths,
    b.delinq_amnt,

    -- ratios
    l.loan_amnt / nullif(b.annual_inc, 0) as loan_to_income,
    12 * l.installment / nullif(b.annual_inc, 0) as payment_to_income,
    b.revol_bal / nullif(b.annual_inc, 0) as revol_bal_to_income
from l
join b on b.borrower_id = l.borrower_id
