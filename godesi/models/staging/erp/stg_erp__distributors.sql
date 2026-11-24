-- One row per distributor.

with source as (

    select * from {{ source('erp', 'distributors') }}

),

renamed as (

    select
        trim(distributor_id)            as distributor_id,
        trim(distributor_name)          as distributor_name,
        trim(city)                      as city_raw,
        {{ city_key('city') }}          as city_key,
        trim(state)                     as state,
        trim(region)                    as region,
        try_to_date(onboarded_date)     as onboarded_date,
        _loaded_at

    from source

)

select * from renamed
