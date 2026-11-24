-- One row per website customer.

with source as (

    select * from {{ source('ecom', 'customers') }}

),

renamed as (

    select
        trim(customer_id)                                       as customer_id,
        trim(full_name)                                         as full_name,
        lower(trim(email))                                      as email,           -- some arrive in CAPITALS
        right(regexp_replace(phone, '[^0-9]', ''), 10)          as phone_number,    -- '+91-98765-43210' -> '9876543210'
        trim(city)                                              as city_raw,
        {{ city_key('city') }}                                  as city_key,
        trim(state)                                             as state,
        trim(pincode)                                           as pincode,
        {{ parse_timestamp('signup_at') }}                      as signed_up_at,
        lower(trim(acquisition_source))                         as acquisition_source,
        _loaded_at

    from source

)

select * from renamed
