-- Q1, Q4: daily sales. Grain: one row per day x channel x region x category.

with items    as (select * from {{ ref('fct_order_items') }}),
     products as (select sku_id, category from {{ ref('dim_products') }}),
     geo      as (select city, region from {{ ref('dim_geography') }}),
     channels as (select channel, channel_type from {{ ref('dim_channels') }}),
     dates    as (select date_day, is_festival_season, upcoming_festival from {{ ref('dim_date') }})

select
    items.order_date,
    items.channel,
    channels.channel_type,
    coalesce(geo.region, 'Unknown')                                         as region,
    coalesce(products.category, 'Unknown')                                  as category,
    dates.is_festival_season,
    dates.upcoming_festival,
    count(distinct iff(not items.is_cancelled, items.order_id, null))       as orders,
    sum(iff(items.is_cancelled or items.is_returned, 0, items.quantity))    as units_sold,
    sum(iff(items.is_cancelled, 0, items.gross_amount_inr))                 as gross_amount_inr,
    sum(iff(items.is_cancelled, 0, items.discount_inr))                     as discount_inr,
    sum(items.net_revenue_inr)                                              as net_revenue_inr,
    sum(items.gross_profit_inr)                                             as gross_profit_inr

from items
left join products on items.sku_id     = products.sku_id
left join geo      on items.city       = geo.city
left join channels on items.channel    = channels.channel
left join dates    on items.order_date = dates.date_day
group by all
