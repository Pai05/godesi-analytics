{#
    Clean-up after a CI run: drops the throw-away CI_PR_<n> schema so it stops using storage.

        dbt run-operation drop_ci_schema --target ci

    Refuses to run on any target other than ci, and only drops schemas whose name starts
    with CI_, so it can never touch DBT_DEV or the prod schemas.
#}
{% macro drop_ci_schema() %}
    {%- set schema_name = target.schema | upper -%}
    {%- if target.name != 'ci' or not schema_name.startswith('CI_') -%}
        {{ exceptions.raise_compiler_error("drop_ci_schema only runs on target ci with a CI_ schema, got " ~ target.name ~ " / " ~ schema_name) }}
    {%- endif -%}
    {% do run_query('drop schema if exists ' ~ target.database ~ '.' ~ schema_name ~ ' cascade') %}
    {{ log('Dropped schema ' ~ target.database ~ '.' ~ schema_name, info=true) }}
{% endmacro %}
