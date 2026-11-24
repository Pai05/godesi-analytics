-- Q5: do website customers come back? Grain: one row per cohort month x months since first order.
-- retention_pct = customers from the cohort who ordered in that month / cohort size.

with customers as (

    select customer_id, cohort_month
    from {{ ref('dim_customers') }}
    where cohort_month is not null

),

orders as (

    select
        customer_id,
        date_trunc('month', order_date)::date   as order_month,
        net_revenue_inr
    from {{ ref('fct_orders') }}
    where channel = 'website' and not is_cancelled

),

activity as (

    select
        customers.cohort_month,
        datediff(month, customers.cohort_month, orders.order_month)    as months_since_first_order,
        count(distinct orders.customer_id)                             as active_customers,
        sum(orders.net_revenue_inr)                                    as net_revenue_inr
    from orders
    inner join customers on orders.customer_id = customers.customer_id
    group by all

),

cohort_size as (

    select cohort_month, count(*) as cohort_customers
    from customers
    group by cohort_month

)

select
    activity.cohort_month,
    activity.months_since_first_order,
    cohort_size.cohort_customers,
    activity.active_customers,
    round(activity.active_customers / cohort_size.cohort_customers * 100, 1)  as retention_pct,
    activity.net_revenue_inr
from activity
inner join cohort_size on activity.cohort_month = cohort_size.cohort_month
