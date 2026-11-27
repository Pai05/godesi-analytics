-- One row per GoDesi SKU, with real nutrition data where Open Food Facts lists the barcode.
-- Plus one "Unknown product" row for every SKU that appears on an order line but is missing
-- from the product master (today only GD-9999). That way reports show "Unknown" instead of
-- (Blank) and the revenue still counts in totals.

with products as (select * from {{ ref('stg_erp__products') }}),
     off      as (select * from {{ ref('stg_off__products') }}),

unknown_skus as (
    select distinct lines.sku_id
    from {{ ref('int_sales_lines__enriched') }} as lines
    left join products on lines.sku_id = products.sku_id
    where products.sku_id is null
      and lines.sku_id is not null
)

select
    products.sku_id,
    products.barcode,
    products.product_name,
    products.category,
    products.sub_category,
    products.pack_size,
    products.mrp_inr,
    products.cost_inr,
    round((products.mrp_inr - products.cost_inr) / nullif(products.mrp_inr, 0) * 100, 1)  as mrp_margin_pct,
    products.launch_date,
    products.is_active,
    off.barcode is not null                                     as is_on_open_food_facts,
    off.nutriscore_grade,
    off.nova_group,
    off.energy_kcal_100g,
    off.sugars_100g

from products
left join off on products.barcode = off.barcode

union all

select
    sku_id,
    null                                    as barcode,
    'Unknown product (' || sku_id || ')'    as product_name,
    'Unknown'                               as category,
    'Unknown'                               as sub_category,
    null                                    as pack_size,
    null                                    as mrp_inr,
    null                                    as cost_inr,
    null                                    as mrp_margin_pct,
    null                                    as launch_date,
    false                                   as is_active,
    false                                   as is_on_open_food_facts,
    null                                    as nutriscore_grade,
    null                                    as nova_group,
    null                                    as energy_kcal_100g,
    null                                    as sugars_100g
from unknown_skus
