-- One row per invoice line.

with source as (

    select * from {{ source('erp', 'invoice_lines') }}

),

renamed as (

    select
        trim(invoice_id) || '-' || trim(line_no)        as invoice_line_id,
        trim(invoice_id)                                as invoice_id,
        try_to_number(line_no)                          as line_no,
        trim(sku_id)                                    as sku_id,
        try_to_number(quantity_units)                   as quantity,
        {{ clean_amount('unit_price_inr') }}            as unit_price_inr,
        {{ clean_amount('scheme_discount_inr') }}       as discount_inr,
        _loaded_at

    from source

),

final as (

    select
        *,
        quantity * unit_price_inr                       as gross_amount_inr,
        quantity * unit_price_inr - discount_inr        as net_amount_inr
    from renamed

)

select * from final
