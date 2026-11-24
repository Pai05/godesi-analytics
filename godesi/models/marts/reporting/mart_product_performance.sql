-- Q2: which SKUs drive revenue and margin. Grain: one row per month x SKU.

with items    as (select * from {{ ref('fct_order_items') }}),
     products as (select * from {{ ref('dim_products') }}),

monthly as (

    select
        date_trunc('month', items.order_date)::date                         as month_start,
        items.sku_id,
        coalesce(products.product_name, 'Unknown SKU')                      as product_name,
        coalesce(products.category, 'Unknown')                              as category,
        sum(iff(items.is_cancelled or items.is_returned, 0, items.quantity)) as units_sold,
        sum(items.net_revenue_inr)                                          as net_revenue_inr,
        sum(items.gross_profit_inr)                                         as gross_profit_inr
    from items
    left join products on items.sku_id = products.sku_id
    group by all

)

select
    *,
    round(gross_profit_inr / nullif(net_revenue_inr, 0) * 100, 2)                  as gross_margin_pct,
    rank() over (partition by month_start order by net_revenue_inr desc)            as revenue_rank_in_month
from monthly
