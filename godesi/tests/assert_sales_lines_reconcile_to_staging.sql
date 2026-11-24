-- Singular test: every staging order line appears exactly once in int_sales_lines__unioned.
-- A test PASSES when this query returns no rows. It returns one row if the counts differ
-- (e.g. an inner join silently dropped lines whose order header is missing).

with expected as (

    select
        (select count(*) from {{ ref('stg_ecom__order_items') }})
      + (select count(*) from {{ ref('stg_marketplace__order_items') }})
      + (select count(*) from {{ ref('stg_erp__invoice_lines') }})        as row_count,

        (select sum(net_amount_inr) from {{ ref('stg_ecom__order_items') }})
      + (select sum(net_amount_inr) from {{ ref('stg_marketplace__order_items') }})
      + (select sum(net_amount_inr) from {{ ref('stg_erp__invoice_lines') }}) as net_amount

),

actual as (

    select count(*) as row_count, sum(net_amount_inr) as net_amount
    from {{ ref('int_sales_lines__unioned') }}

)

select
    expected.row_count  as expected_rows,
    actual.row_count    as actual_rows,
    expected.net_amount as expected_net_amount,
    actual.net_amount   as actual_net_amount
from expected, actual
where expected.row_count != actual.row_count
   or abs(expected.net_amount - actual.net_amount) > 0.01
