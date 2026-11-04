{#-
  One row per Lending Club loan, typed and renamed.

  Dropped here and never used downstream: free text and identifiers that are
  not needed for modeling (url, desc, emp_title, title, member_id, zip_code).
  Post-origination fields are kept, because core.outcomes needs some of them;
  the feature layer selects only from an allow-list (see M2).
-#}

{%- set application_numeric = [
    'loan_amnt', 'int_rate', 'installment', 'annual_inc', 'annual_inc_joint', 'dti', 'dti_joint',
    'delinq_2yrs', 'fico_range_low', 'fico_range_high', 'inq_last_6mths',
    'mths_since_last_delinq', 'mths_since_last_record', 'open_acc', 'pub_rec', 'revol_bal',
    'revol_util', 'total_acc', 'collections_12_mths_ex_med', 'mths_since_last_major_derog',
    'acc_now_delinq', 'tot_coll_amt', 'tot_cur_bal', 'total_rev_hi_lim', 'acc_open_past_24mths',
    'avg_cur_bal', 'bc_open_to_buy', 'bc_util', 'chargeoff_within_12_mths', 'delinq_amnt',
    'mo_sin_old_il_acct', 'mo_sin_old_rev_tl_op', 'mo_sin_rcnt_rev_tl_op', 'mo_sin_rcnt_tl',
    'mort_acc', 'mths_since_recent_bc', 'mths_since_recent_inq', 'num_accts_ever_120_pd',
    'num_actv_bc_tl', 'num_actv_rev_tl', 'num_bc_sats', 'num_bc_tl', 'num_il_tl', 'num_op_rev_tl',
    'num_rev_accts', 'num_rev_tl_bal_gt_0', 'num_sats', 'num_tl_120dpd_2m', 'num_tl_30dpd',
    'num_tl_90g_dpd_24m', 'num_tl_op_past_12m', 'pct_tl_nvr_dlq', 'percent_bc_gt_75',
    'pub_rec_bankruptcies', 'tax_liens', 'tot_hi_cred_lim', 'total_bal_ex_mort', 'total_bc_limit',
    'total_il_high_credit_limit',
] -%}

{%- set post_origination_numeric = [
    'funded_amnt', 'funded_amnt_inv', 'out_prncp', 'out_prncp_inv', 'total_pymnt',
    'total_pymnt_inv', 'total_rec_prncp', 'total_rec_int', 'total_rec_late_fee', 'recoveries',
    'collection_recovery_fee', 'last_pymnt_amnt', 'last_fico_range_high', 'last_fico_range_low',
    'settlement_amount',
] -%}

with source as (
    select * from {{ source('raw', 'lc_accepted') }}
    -- The file ends with summary lines ("Total amount funded in policy code ...") that have no id.
    where try_cast(id as bigint) is not null
)

select
    cast(id as bigint) as loan_id,
    {{ lc_month('issue_d') }} as issue_date,
    cast(trim(replace(term, 'months', '')) as integer) as term_months,
    grade,
    sub_grade,
    nullif(emp_length, 'n/a') as emp_length,
    home_ownership,
    verification_status,
    purpose,
    addr_state,
    initial_list_status,
    application_type,
    {{ lc_month('earliest_cr_line') }} as earliest_cr_line_date,
    {%- for col in application_numeric %}
    try_cast({{ col }} as double) as {{ col }},
    {%- endfor %}

    -- outcome and post-origination fields
    loan_status,
    {{ lc_month('last_pymnt_d') }} as last_pymnt_date,
    {{ lc_month('last_credit_pull_d') }} as last_credit_pull_date,
    pymnt_plan,
    hardship_flag,
    debt_settlement_flag,
    {%- for col in post_origination_numeric %}
    try_cast({{ col }} as double) as {{ col }},
    {%- endfor %}

    _source_file,
    _loaded_at,
    _row_hash
from source
