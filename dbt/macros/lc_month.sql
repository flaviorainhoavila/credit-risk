{#- Lending Club month strings such as 'Dec-2015' to the first day of that month. -#}
{% macro lc_month(col) -%}
    cast(strptime({{ col }}, '%b-%Y') as date)
{%- endmacro %}
