-- Q3: how each channel performs, month by month. Grain: one row per month x channel.

with items    as (select * from {{ ref('fct_order_items') }}),
     channels as (select * from {{ ref('dim_channels') }}),

monthly as (

    select
        date_trunc('month', items.order_date)::date                         as month_start,
        items.channel,
        channels.channel_name,
        channels.channel_type,
        count(distinct iff(not items.is_cancelled, items.order_id, null))   as orders,
        count(distinct iff(items.is_cancelled, items.order_id, null))       as cancelled_orders,
        sum(iff(items.is_cancelled, 0, items.gross_amount_inr))             as gross_amount_inr,
        sum(iff(items.is_cancelled, 0, items.discount_inr))                 as discount_inr,
        sum(items.net_revenue_inr)                                          as net_revenue_inr,
        sum(items.commission_cost_inr)                                      as commission_inr,
        sum(items.gross_profit_inr)                                         as gross_profit_inr,
        count_if(items.is_returned)                                         as returned_lines,
        count_if(not items.is_cancelled)                                    as kept_lines
    from items
    left join channels on items.channel = channels.channel
    group by all

)

select
    *,
    round(net_revenue_inr / nullif(orders, 0), 2)                                       as aov_inr,
    round(discount_inr / nullif(gross_amount_inr, 0) * 100, 2)                          as discount_pct,
    round(returned_lines / nullif(kept_lines, 0) * 100, 2)                              as return_rate_pct,
    round(gross_profit_inr / nullif(net_revenue_inr, 0) * 100, 2)                       as gross_margin_pct,
    round(net_revenue_inr / nullif(sum(net_revenue_inr) over (partition by month_start), 0) * 100, 2)
                                                                                        as revenue_share_pct,
    round((net_revenue_inr / nullif(lag(net_revenue_inr) over (partition by channel order by month_start), 0) - 1) * 100, 1)
                                                                                        as mom_growth_pct
from monthly
