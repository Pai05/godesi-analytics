-- One row per website order line.

with source as (

    select * from {{ source('ecom', 'order_items') }}

),

renamed as (

    select
        trim(order_item_id)                     as order_item_id,
        trim(order_id)                          as order_id,
        trim(sku_id)                            as sku_id,
        try_to_number(quantity)                 as quantity,
        {{ clean_amount('unit_price_inr') }}    as unit_price_inr,      -- '₹40.00' / 'Rs. 40' / '40.00'
        {{ clean_amount('discount_inr') }}      as discount_inr,
        _loaded_at

    from source

),

final as (

    select
        *,
        quantity * unit_price_inr                   as gross_amount_inr,
        quantity * unit_price_inr - discount_inr    as net_amount_inr
    from renamed

)

select * from final
