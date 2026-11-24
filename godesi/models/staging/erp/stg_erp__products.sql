-- One row per SKU: cleaned, typed, latest version only.

with source as (

    select * from {{ source('erp', 'products') }}

),

renamed as (

    select
        trim(sku_id)                        as sku_id,
        trim(barcode)                       as barcode,
        trim(product_name)                  as product_name,
        initcap(trim(category))             as category,        -- 'candy' -> 'Candy'
        trim(sub_category)                  as sub_category,
        trim(pack_size)                     as pack_size,
        try_to_number(mrp_inr, 10, 2)       as mrp_inr,
        try_to_number(cost_inr, 10, 2)      as cost_inr,
        try_to_date(launch_date)            as launch_date,
        upper(trim(is_active)) = 'Y'        as is_active,
        try_to_timestamp_ntz(updated_at)    as updated_at,
        _loaded_at

    from source

),

latest as (

    -- batch 2 re-sends changed SKUs: keep only the newest row per sku_id
    select *
    from renamed
    qualify row_number() over (partition by sku_id order by updated_at desc, _loaded_at desc) = 1

)

select * from latest
