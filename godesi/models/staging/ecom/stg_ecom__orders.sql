-- One row per website order: latest known status.
-- The raw table has exact duplicate rows, and each load can add a newer row for the
-- same order (placed -> shipped -> delivered ...). We keep the newest one.

with source as (

    select * from {{ source('ecom', 'orders') }}

),

renamed as (

    select
        trim(order_id)                              as order_id,
        trim(customer_id)                           as customer_id,
        {{ parse_timestamp('order_ts') }}           as ordered_at,          -- two formats in the raw data
        lower(trim(status))                         as order_status,
        trim(payment_method)                        as payment_method,
        nullif(trim(promo_code), '')                as promo_code,
        trim(shipping_city)                         as shipping_city_raw,
        {{ city_key('shipping_city') }}             as city_key,
        trim(shipping_state)                        as shipping_state,
        trim(shipping_pincode)                      as shipping_pincode,
        {{ clean_amount('shipping_fee_inr') }}      as shipping_fee_inr,
        {{ parse_timestamp('updated_at') }}         as updated_at,
        _loaded_at

    from source

),

latest as (

    select *
    from renamed
    qualify row_number() over (partition by order_id order by updated_at desc, _loaded_at desc) = 1

)

select * from latest
