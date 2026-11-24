-- One row per returned website order line.

with source as (

    select * from {{ source('ecom', 'returns') }}

),

renamed as (

    select
        trim(return_id)                         as return_id,
        trim(order_item_id)                     as order_item_id,
        {{ parse_timestamp('return_ts') }}      as returned_at,
        trim(reason)                            as return_reason,
        {{ clean_amount('refund_inr') }}        as refund_inr,
        _loaded_at

    from source

)

select * from renamed
