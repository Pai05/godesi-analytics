-- One row per marketplace order line (exact duplicate rows removed).
-- seller_sku is NOT yet a GoDesi sku_id: Amazon/Flipkart send the barcode,
-- quick-commerce apps send the sku_id. Mapping happens in the intermediate layer.

with source as (

    select * from {{ source('marketplace', 'order_items') }}

),

renamed as (

    select
        trim(marketplace_order_id) || '-' || trim(line_number)  as marketplace_order_item_id,
        trim(marketplace_order_id)                              as marketplace_order_id,
        try_to_number(line_number)                              as line_number,
        upper(trim(seller_sku))                                 as seller_sku,          -- ' gd-0001 ' -> 'GD-0001'
        try_to_number(quantity)                                 as quantity,
        {{ clean_amount('selling_price_inr') }}                 as unit_price_inr,
        {{ clean_amount('platform_discount_inr') }}             as discount_inr,
        {{ clean_amount('commission_inr') }}                    as commission_inr,
        _loaded_at

    from source

),

deduplicated as (

    select *
    from renamed
    qualify row_number() over (partition by marketplace_order_item_id order by _loaded_at desc) = 1

),

final as (

    select
        *,
        quantity * unit_price_inr                   as gross_amount_inr,
        quantity * unit_price_inr - discount_inr    as net_amount_inr
    from deduplicated

)

select * from final
