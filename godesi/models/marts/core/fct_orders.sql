-- Fact table. Grain: one row per order (website order, marketplace order or invoice).

select
    order_id,
    any_value(channel)              as channel,
    min(order_date)                 as order_date,
    min(ordered_at)                 as ordered_at,
    any_value(customer_id)          as customer_id,
    any_value(store_id)             as store_id,
    any_value(distributor_id)       as distributor_id,
    any_value(city)                 as city,
    any_value(order_status)         as order_status,
    boolor_agg(is_cancelled)        as is_cancelled,
    boolor_agg(is_returned)         as has_returned_items,
    count(*)                        as line_count,
    sum(quantity)                   as units,
    sum(gross_amount_inr)           as gross_amount_inr,
    sum(discount_inr)               as discount_inr,
    sum(net_revenue_inr)            as net_revenue_inr,
    sum(cogs_inr)                   as cogs_inr,
    sum(commission_cost_inr)        as commission_cost_inr,
    sum(gross_profit_inr)           as gross_profit_inr,
    max(updated_at)                 as updated_at

from {{ ref('fct_order_items') }}
group by order_id
