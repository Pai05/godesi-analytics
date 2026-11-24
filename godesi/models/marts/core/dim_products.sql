-- One row per GoDesi SKU, with real nutrition data where Open Food Facts lists the barcode.

with products as (select * from {{ ref('stg_erp__products') }}),
     off      as (select * from {{ ref('stg_off__products') }})

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
