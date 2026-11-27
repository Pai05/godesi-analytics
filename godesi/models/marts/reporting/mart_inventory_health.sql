-- Q6: are we stocking out or overstocking? Grain: one row per day x SKU (all warehouses).
-- days_of_cover = stock on hand / average units sold per day over the last 28 days.

with stock as (

    select
        snapshot_date,
        sku_id,
        sum(on_hand_units)              as on_hand_units,
        count_if(on_hand_units = 0)     as warehouses_out_of_stock,
        count(*)                        as warehouses
    from {{ ref('stg_inventory__stock_daily') }}
    group by snapshot_date, sku_id

),

sales as (

    -- units that left the warehouse (returns came back later, cancellations never left)
    select order_date, sku_id, sum(iff(is_cancelled, 0, quantity)) as units_sold
    from {{ ref('fct_order_items') }}
    group by order_date, sku_id

),

joined as (

    select
        stock.*,
        coalesce(sales.units_sold, 0)   as units_sold
    from stock
    left join sales
        on stock.snapshot_date = sales.order_date
       and stock.sku_id = sales.sku_id

),

with_demand as (

    select
        *,
        avg(units_sold) over (
            partition by sku_id order by snapshot_date
            rows between 27 preceding and current row
        )                               as avg_daily_units_28d
    from joined

)

select
    with_demand.snapshot_date,
    with_demand.sku_id,
    products.product_name,
    products.category,
    with_demand.on_hand_units,
    with_demand.units_sold,
    round(with_demand.avg_daily_units_28d, 2)                                       as avg_daily_units_28d,
    round(with_demand.on_hand_units / nullif(with_demand.avg_daily_units_28d, 0), 1) as days_of_cover,
    with_demand.warehouses_out_of_stock,
    case
        when with_demand.warehouses_out_of_stock > 0                                     then 'Stock-out'
        when with_demand.on_hand_units / nullif(with_demand.avg_daily_units_28d, 0) < 7  then 'Low'
        when with_demand.on_hand_units / nullif(with_demand.avg_daily_units_28d, 0) > 60 then 'Overstock'
        else 'Healthy'
    end                                                                             as stock_status

from with_demand
left join {{ ref('dim_products') }} as products
    on with_demand.sku_id = products.sku_id
