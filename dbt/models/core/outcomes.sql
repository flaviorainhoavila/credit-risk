{#-
  Final status at the snapshot and the binary label.

  Label (docs/assumptions.md): bad = Charged Off or Default, good = Fully Paid,
  including the "Does not meet the credit policy" variants. Current, In Grace and
  Late loans are unresolved: is_bad is null.
-#}
with s as (
    select
        loan_id,
        issue_date,
        term_months,
        loan_status,
        last_pymnt_date,
        replace(loan_status, 'Does not meet the credit policy. Status:', '') as base_status,
        starts_with(loan_status, 'Does not meet the credit policy') as off_policy
    from {{ ref('stg_lc__loans') }}
)

select
    loan_id,
    loan_status,
    base_status,
    off_policy,
    base_status in ('Fully Paid', 'Charged Off', 'Default') as is_resolved,
    case
        when base_status in ('Charged Off', 'Default') then 1
        when base_status = 'Fully Paid' then 0
    end as is_bad,
    last_pymnt_date,
    cast('{{ var("snapshot_date") }}' as date) as snapshot_date,
    date_diff('month', issue_date, cast('{{ var("snapshot_date") }}' as date)) as months_observed,
    -- Matured: the full term had elapsed by the snapshot date.
    date_diff('month', issue_date, cast('{{ var("snapshot_date") }}' as date)) >= term_months
        as is_matured
from s
