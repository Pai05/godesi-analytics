{#
    Where does each model go?

    dbt's default would create schemas like DBT_DEV_STAGING. We want instead:
      - prod target: the folder's schema as-is      -> STAGING, INTERMEDIATE, MARTS, SNAPSHOTS
      - any other target (dev, ci): the target schema -> DBT_DEV (one sandbox per developer)
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'prod' and custom_schema_name is not none -%}
        {{ custom_schema_name | trim | upper }}
    {%- else -%}
        {{ target.schema | trim | upper }}
    {%- endif -%}
{%- endmacro %}
