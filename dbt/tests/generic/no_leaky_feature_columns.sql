{#- Fails for every column of the model that column_policy marks as post-origination or outcome. -#}
{% test no_leaky_feature_columns(model) %}
select c.column_name
from information_schema.columns c
join {{ ref('column_policy') }} p on lower(p.column_name) = lower(c.column_name)
where c.table_schema = '{{ model.schema }}'
  and c.table_name = '{{ model.identifier }}'
  and p.category in ('post_origination', 'outcome')
{% endtest %}
