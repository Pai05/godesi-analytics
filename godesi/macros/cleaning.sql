{#  Reusable cleaning helpers for staging models.  #}


{#  '₹40.00', 'Rs. 40', ' 40.00 ' -> 40.00  (NULL if still not a number)  #}
{% macro clean_amount(column, scale=2) -%}
    try_to_number(trim(regexp_replace({{ column }}, $$^\s*(₹|Rs\.?)\s*$$, '')), 14, {{ scale }})
{%- endmacro %}


{#  Every timestamp format found in the sources, all in Indian time (IST):
      '2024-03-01 14:22:10'          ERP, website, Flipkart, quick commerce
      '01/03/2024 14:22'             some website orders (day first)
      '2024-03-01T14:22:10+05:30'    Amazon (offset dropped: already IST)
      '2024-03-01T14:22:10Z'         Open Food Facts (UTC)                     #}
{% macro parse_timestamp(column) -%}
    coalesce(
        try_to_timestamp_ntz({{ column }}, 'YYYY-MM-DD HH24:MI:SS'),
        try_to_timestamp_ntz({{ column }}, 'DD/MM/YYYY HH24:MI'),
        try_to_timestamp_ntz(left({{ column }}, 19), 'YYYY-MM-DD"T"HH24:MI:SS')
    )
{%- endmacro %}


{#  Join key for the city_mapping seed: ' BANGALORE ' -> 'bangalore'  #}
{% macro city_key(column) -%}
    lower(trim({{ column }}))
{%- endmacro %}
