-- One row per distributor-to-store invoice.

with source as (

    select * from {{ source('erp', 'invoices') }}

),

renamed as (

    select
        trim(invoice_id)                                as invoice_id,
        trim(distributor_id)                            as distributor_id,
        trim(store_id)                                  as store_id,
        try_to_date(invoice_date, 'DD-MM-YYYY')         as invoice_date,     -- ERP sends DD-MM-YYYY
        trim(payment_terms)                             as payment_terms,
        _loaded_at

    from source

)

select * from renamed
