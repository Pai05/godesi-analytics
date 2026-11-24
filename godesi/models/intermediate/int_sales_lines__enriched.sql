-- All order lines + product, geography, channel type, and money we actually keep.
-- Grain: one row per order line (same as int_sales_lines__unioned).
--
-- Business rules:
--   net_revenue_inr   = net_amount_inr, but 0 for cancelled or returned lines
--   cogs_inr          = quantity x unit cost, only for lines we actually sold
--   gross_profit_inr  = net_revenue_inr - cogs_inr - marketplace commission

with lines    as (select * from {{ ref('int_sales_lines__unioned') }}),
     products as (select * from {{ ref('stg_erp__products') }}),
     cities   as (select * from {{ ref('city_mapping') }}),
     channels as (select * from {{ ref('channel_mapping') }}),

enriched as (

    select
        lines.*,
        lines.ordered_at::date                              as order_date,
        channels.channel_name,
        channels.channel_type,
        products.product_name,
        products.category,
        products.sub_category,
        products.cost_inr                                   as unit_cost_inr,
        cities.city,
        cities.state,
        cities.region,
        cities.is_metro,
        lines.order_status = 'cancelled'                    as is_cancelled

    from lines
    left join products on lines.sku_id   = products.sku_id
    left join cities   on lines.city_key = cities.city_key
    left join channels on lines.channel  = channels.channel

),

final as (

    select
        *,
        iff(is_cancelled or is_returned, 0, net_amount_inr)                 as net_revenue_inr,
        iff(is_cancelled or is_returned, 0, quantity * unit_cost_inr)       as cogs_inr,
        iff(is_cancelled, 0, commission_inr)                                as commission_cost_inr,
        net_revenue_inr - cogs_inr - commission_cost_inr                    as gross_profit_inr
    from enriched

)

select * from final
