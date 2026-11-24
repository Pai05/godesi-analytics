-- One row per promotion code.

with source as (

    select * from {{ source('erp', 'promotions') }}

),

renamed as (

    select
        trim(promo_code)                        as promo_code,
        trim(promo_name)                        as promo_name,
        lower(trim(channel))                    as promo_channel,   -- website / amazon / flipkart / quick_commerce / all
        try_to_number(discount_pct, 5, 2)       as discount_pct,
        try_to_date(start_date)                 as start_date,
        try_to_date(end_date)                   as end_date,
        _loaded_at

    from source

)

select * from renamed
