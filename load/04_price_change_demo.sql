/* =====================================================================
   GoDesi Analytics — Phase 5: price-change demo for the dbt snapshot
   ---------------------------------------------------------------------
   Run ONLY after the first `dbt snapshot`. It simulates the ERP sending
   two new price records on 5 Jan 2026:
     GD-0001 Desi Popz Tangy Imli : MRP -> 50.00
     GD-0006 Kaju Katli           : MRP -> 349.00
   Then run `dbt snapshot` again and query the history (see Phase 5 steps).
   ===================================================================== */

USE ROLE LOADER;
USE WAREHOUSE GODESI_WH;

INSERT INTO GODESI_RAW.ERP.PRODUCTS (
    sku_id, barcode, product_name, category, sub_category, pack_size,
    mrp_inr, cost_inr, launch_date, is_active, updated_at,
    _source_file, _source_row_number, _loaded_at
)
SELECT
    sku_id, barcode, product_name, category, sub_category, pack_size,
    CASE sku_id WHEN 'GD-0001' THEN '50.00' WHEN 'GD-0006' THEN '349.00' END,
    cost_inr, launch_date, is_active, '2026-01-05 09:00:00',
    'manual_price_change_demo', 1, CURRENT_TIMESTAMP()
FROM GODESI_RAW.ERP.PRODUCTS
WHERE sku_id IN ('GD-0001', 'GD-0006')
QUALIFY ROW_NUMBER() OVER (PARTITION BY sku_id ORDER BY updated_at DESC) = 1;

-- Expect: number of rows inserted = 2
SELECT sku_id, product_name, mrp_inr, updated_at
FROM GODESI_RAW.ERP.PRODUCTS
WHERE sku_id IN ('GD-0001', 'GD-0006')
ORDER BY sku_id, updated_at;
