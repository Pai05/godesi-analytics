-- One row per website customer, with lifetime order stats and cohort month.
-- Cohort = month of the first non-cancelled website order.

with customers as (select * from {{ ref('stg_ecom__customers') }}),
     cities    as (select * from {{ ref('city_mapping') }}),

orders as (

    select
        customer_id,
        order_id,
        min(order_date)         as order_date,
        sum(net_revenue_inr)    as net_revenue_inr
    from {{ ref('int_sales_lines__enriched') }}
    where channel = 'website' and not is_cancelled
    group by customer_id, order_id

),

customer_orders as (

    select
        customer_id,
        min(order_date)         as first_order_date,
        max(order_date)         as last_order_date,
        count(*)                as lifetime_orders,
        sum(net_revenue_inr)    as lifetime_revenue_inr
    from orders
    group by customer_id

)

select
    customers.customer_id,
    customers.full_name,
    customers.email,
    customers.phone_number,
    cities.city,
    cities.state,
    cities.region,
    customers.pincode,
    customers.signed_up_at,
    customers.acquisition_source,
    customer_orders.first_order_date,
    customer_orders.last_order_date,
    date_trunc('month', customer_orders.first_order_date)::date        as cohort_month,
    coalesce(customer_orders.lifetime_orders, 0)                        as lifetime_orders,
    coalesce(customer_orders.lifetime_revenue_inr, 0)                   as lifetime_revenue_inr,
    case
        when coalesce(customer_orders.lifetime_orders, 0) = 0 then 'Prospect'
        when customer_orders.lifetime_orders = 1              then 'One-time'
        when customer_orders.lifetime_orders <= 3             then 'Repeat'
        else 'Loyal'
    end                                                                 as customer_segment

from customers
left join cities          on customers.city_key   = cities.city_key
left join customer_orders on customers.customer_id = customer_orders.customer_id
