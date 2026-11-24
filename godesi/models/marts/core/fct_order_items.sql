-- Fact table. Grain: one row per order line, all channels.
-- Only keys, flags and measures; descriptive attributes live in the dim_ tables.
--
-- INCREMENTAL: the first run (or --full-refresh) builds the whole table. Later runs only
-- take lines whose order changed recently and MERGE them on sales_line_id:
--   new line            -> inserted
--   known line, changed -> updated in place (e.g. status shipped -> delivered)

{{
    config(
        materialized         = 'incremental',
        unique_key           = 'sales_line_id',
        incremental_strategy = 'merge',
        on_schema_change     = 'append_new_columns'
    )
}}

select
    -- keys
    sales_line_id,
    order_id,
    channel,                -- -> dim_channels
    order_date,             -- -> dim_date
    sku_id,                 -- -> dim_products
    customer_id,            -- -> dim_customers (website only)
    store_id,               -- offline only
    distributor_id,         -- offline only
    city,                   -- -> dim_geography

    -- status
    ordered_at,
    order_status,
    is_cancelled,
    is_returned,

    -- measures (INR)
    quantity,
    unit_price_inr,
    gross_amount_inr,
    discount_inr,
    net_amount_inr,
    refund_inr,
    net_revenue_inr,
    cogs_inr,
    commission_cost_inr,
    gross_profit_inr,

    updated_at

from {{ ref('int_sales_lines__enriched') }}

{% if is_incremental() %}
-- {{ this }} = the existing fct_order_items table. Look back 3 days before its newest
-- change so late-arriving updates are not missed; MERGE makes re-processing them harmless.
where updated_at >= (select dateadd(day, -3, max(updated_at)) from {{ this }})
{% endif %}
