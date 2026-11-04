-- Loan terms and pricing as set at origination. One row per loan.
select
    loan_id,
    -- ASSUMPTION: the public file has no borrower key (member_id is empty), so each loan
    -- gets its own anonymous borrower profile, keyed by the loan id.
    loan_id as borrower_id,
    issue_date,
    year(issue_date) as issue_year,
    term_months,
    loan_amnt,
    int_rate,
    installment,
    grade,
    sub_grade,
    purpose,
    initial_list_status,
    application_type,
    verification_status
from {{ ref('stg_lc__loans') }}
