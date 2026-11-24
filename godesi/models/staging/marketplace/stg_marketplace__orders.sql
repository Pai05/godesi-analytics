-- One row per marketplace order (Amazon, Flipkart, quick commerce): latest known status.

with source as (

    select * from {{ source('marketplace', 'orders') }}

),

renamed as (

    select
        trim(marketplace_order_id)              as marketplace_order_id,
        lower(trim(channel))                    as channel,
        {{ parse_timestamp('order_date') }}     as ordered_at,          -- Amazon sends ISO with +05:30
        lower(trim(status))                     as order_status,        -- Flipkart sends UPPER CASE
        trim(buyer_city)                        as buyer_city_raw,
        {{ city_key('buyer_city') }}            as city_key,
        trim(buyer_state)                       as buyer_state,
        trim(buyer_pincode)                     as buyer_pincode,
        {{ parse_timestamp('updated_at') }}     as updated_at,
        _loaded_at

    from source

),

latest as (

    select *
    from renamed
    qualify row_number() over (partition by marketplace_order_id order by updated_at desc, _loaded_at desc) = 1

)

select * from latest
