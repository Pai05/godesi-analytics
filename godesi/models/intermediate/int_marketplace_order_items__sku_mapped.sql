-- Marketplace order lines with a GoDesi sku_id.
-- Amazon and Flipkart identify products by barcode; Blinkit, Zepto and Instamart use our
-- own sku_id. A lookup with both keys translates either one.

with items as (

    select * from {{ ref('stg_marketplace__order_items') }}

),

products as (

    select sku_id, barcode from {{ ref('stg_erp__products') }}

),

sku_lookup as (

    select barcode as seller_sku, sku_id, 'barcode' as matched_on from products
    union all
    select sku_id  as seller_sku, sku_id, 'sku_id'  as matched_on from products

)

select
    items.*,
    sku_lookup.sku_id,
    sku_lookup.matched_on

from items
left join sku_lookup
    on items.seller_sku = sku_lookup.seller_sku
