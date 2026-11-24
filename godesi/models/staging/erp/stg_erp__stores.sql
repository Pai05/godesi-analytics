-- One row per retail store.

with source as (

    select * from {{ source('erp', 'stores') }}

),

renamed as (

    select
        trim(store_id)                  as store_id,
        trim(store_name)                as store_name,
        trim(store_type)                as store_type,
        trim(distributor_id)            as distributor_id,
        trim(city)                      as city_raw,
        {{ city_key('city') }}          as city_key,
        trim(state)                     as state,
        trim(pincode)                   as pincode,
        try_to_date(opened_date)        as opened_date,
        _loaded_at

    from source

)

select * from renamed
