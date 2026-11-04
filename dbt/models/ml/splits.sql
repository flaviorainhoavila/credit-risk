{#-
  Modeling population and out-of-time split (docs/assumptions.md): resolved
  36-month loans issued 2007 to 2015, split by issue year.
-#}
select
    l.loan_id,
    l.issue_date,
    l.issue_year,
    o.is_bad,
    case
        when l.issue_year <= {{ var('train_last_year') }} then 'train'
        when l.issue_year = {{ var('validation_year') }} then 'validation'
        else 'test_' || l.issue_year
    end as split
from {{ ref('loans') }} l
join {{ ref('outcomes') }} o using (loan_id)
where l.term_months = 36
  and l.issue_year <= {{ var('last_vintage') }}
  and o.is_resolved
