-- Every order line from every channel in ONE shape. Grain: one row per order line.
--   website      -> stg_ecom__order_items      + stg_ecom__orders      (+ returns)
--   marketplace  -> int_..._sku_mapped         + stg_marketplace__orders
--   offline      -> stg_erp__invoice_lines     + stg_erp__invoices     (+ store for the city)

with

website_lines   as (select * from {{ ref('stg_ecom__order_items') }}),
website_orders  as (select * from {{ ref('stg_ecom__orders') }}),
website_returns as (

    select
        order_item_id,
        sum(refund_inr)     as refund_inr,
        min(returned_at)    as returned_at
    from {{ ref('stg_ecom__returns') }}
    group by order_item_id

),

marketplace_lines  as (select * from {{ ref('int_marketplace_order_items__sku_mapped') }}),
marketplace_orders as (select * from {{ ref('stg_marketplace__orders') }}),

invoice_lines as (select * from {{ ref('stg_erp__invoice_lines') }}),
invoices      as (select * from {{ ref('stg_erp__invoices') }}),
stores        as (select * from {{ ref('stg_erp__stores') }}),


website as (

    select
        l.order_item_id                         as sales_line_id,
        o.order_id                              as order_id,
        'website'                               as channel,
        o.ordered_at,
        o.order_status,
        r.order_item_id is not null             as is_returned,
        o.customer_id,
        cast(null as varchar)                   as store_id,
        cast(null as varchar)                   as distributor_id,
        o.city_key,
        l.sku_id,
        l.quantity,
        l.unit_price_inr,
        l.gross_amount_inr,
        l.discount_inr,
        l.net_amount_inr,
        0                                       as commission_inr,
        coalesce(r.refund_inr, 0)               as refund_inr,
        o.updated_at
    from website_lines as l
    inner join website_orders as o on l.order_id = o.order_id
    left join website_returns as r on l.order_item_id = r.order_item_id

),

marketplace as (

    select
        l.marketplace_order_item_id             as sales_line_id,
        o.marketplace_order_id                  as order_id,
        o.channel,
        o.ordered_at,
        o.order_status,
        o.order_status = 'returned'             as is_returned,      -- whole order returned
        cast(null as varchar)                   as customer_id,      -- marketplaces don't share buyers
        cast(null as varchar)                   as store_id,
        cast(null as varchar)                   as distributor_id,
        o.city_key,
        l.sku_id,
        l.quantity,
        l.unit_price_inr,
        l.gross_amount_inr,
        l.discount_inr,
        l.net_amount_inr,
        l.commission_inr,
        iff(o.order_status = 'returned', l.net_amount_inr, 0) as refund_inr,
        o.updated_at
    from marketplace_lines as l
    inner join marketplace_orders as o on l.marketplace_order_id = o.marketplace_order_id

),

offline as (

    select
        l.invoice_line_id                       as sales_line_id,
        i.invoice_id                            as order_id,
        'offline'                               as channel,
        i.invoice_date::timestamp_ntz           as ordered_at,
        'delivered'                             as order_status,     -- an invoice = goods handed over
        false                                   as is_returned,
        cast(null as varchar)                   as customer_id,
        i.store_id,
        i.distributor_id,
        s.city_key,
        l.sku_id,
        l.quantity,
        l.unit_price_inr,
        l.gross_amount_inr,
        l.discount_inr,
        l.net_amount_inr,
        0                                       as commission_inr,
        0                                       as refund_inr,
        i.invoice_date::timestamp_ntz           as updated_at
    from invoice_lines as l
    inner join invoices as i on l.invoice_id = i.invoice_id
    left join stores as s on i.store_id = s.store_id

)

select * from website
union all
select * from marketplace
union all
select * from offline
