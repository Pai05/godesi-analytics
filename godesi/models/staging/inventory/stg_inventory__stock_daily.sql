-- One row per day x warehouse x SKU: closing stock.

with source as (

    select * from {{ source('inventory', 'stock_daily') }}

),

renamed as (

    select
        {{ dbt_utils.generate_surrogate_key(['snapshot_date', 'warehouse_id', 'sku_id']) }}  as stock_snapshot_id,
        try_to_date(snapshot_date)              as snapshot_date,
        trim(warehouse_id)                      as warehouse_id,
        trim(sku_id)                            as sku_id,
        try_to_number(on_hand_units)            as on_hand_units,
        _loaded_at

    from source

)

select * from renamed
