{#
    Opt-in: build only the last N days of data while developing, to save credits.

        dbt build --vars '{dev_days: 90}'

    Without the var, or on the prod target, it adds nothing and the full data is used.
    The window counts back from the newest date in the data (not from today), because
    the GoDesi data ends in Dec 2025.
#}
{% macro limit_in_dev(date_column, relation) -%}
    {%- if target.name != 'prod' and var('dev_days', none) is not none -%}
    where {{ date_column }} >= (
        select dateadd(day, -{{ var('dev_days') }}, max({{ date_column }})) from {{ relation }}
    )
    {%- endif -%}
{%- endmacro %}
