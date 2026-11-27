-- Q7: did promotions lift sales? Grain: one row per promotion.
-- Lift = average daily net revenue during the promo vs the 28 days before it,
-- in the channels the promo ran on.
-- Caution: festival promos coincide with festival demand, so their lift mixes both effects.

with promos as (

    select * from {{ ref('stg_erp__promotions') }}

),

daily as (

    select order_date, channel, channel_type, sum(net_revenue_inr) as revenue
    from {{ ref('int_sales_lines__enriched') }}
    group by all

),

channels as (

    select distinct channel, channel_type from daily

),

promo_channels as (

    -- which sales channels each promo applies to
    select promos.promo_code, channels.channel
    from promos
    inner join channels
        on promos.promo_channel = 'all'
        or promos.promo_channel = channels.channel
        or (promos.promo_channel = 'quick_commerce' and channels.channel_type = 'Quick Commerce')

),

promo_period as (

    select
        promos.promo_code,
        sum(daily.revenue)                  as revenue,
        count(distinct daily.order_date)    as days
    from promos
    inner join promo_channels on promos.promo_code = promo_channels.promo_code
    inner join daily
        on daily.channel = promo_channels.channel
       and daily.order_date between promos.start_date and promos.end_date
    group by promos.promo_code

),

pre_period as (

    select
        promos.promo_code,
        sum(daily.revenue)                  as revenue,
        count(distinct daily.order_date)    as days
    from promos
    inner join promo_channels on promos.promo_code = promo_channels.promo_code
    inner join daily
        on daily.channel = promo_channels.channel
       and daily.order_date between dateadd(day, -28, promos.start_date) and dateadd(day, -1, promos.start_date)
    group by promos.promo_code

)

select
    promos.promo_code,
    promos.promo_name,
    promos.promo_channel,
    promos.discount_pct,
    promos.start_date,
    promos.end_date,
    datediff(day, promos.start_date, promos.end_date) + 1                            as promo_days,
    round(promo_period.revenue / nullif(promo_period.days, 0), 2)                    as avg_daily_revenue_during,
    round(pre_period.revenue / nullif(pre_period.days, 0), 2)                        as avg_daily_revenue_before,
    round((avg_daily_revenue_during / nullif(avg_daily_revenue_before, 0) - 1) * 100, 1)  as revenue_lift_pct

from promos
left join promo_period on promos.promo_code = promo_period.promo_code
left join pre_period   on promos.promo_code = pre_period.promo_code
