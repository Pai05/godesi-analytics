/* =====================================================================
   GoDesi — final data verification (run before documenting / publishing)
   ---------------------------------------------------------------------
   Where: Snowflake website -> new worksheet -> paste all -> Run All
          (Ctrl + Shift + Enter). The last result is a scorecard table.

   Reads the PROD schemas (STAGING, MARTS) that Power BI and Streamlit use.
   Read-only: it changes nothing.

   Columns of the result:
     section     1 = integrity checks, 2 = numbers shown on the dashboard
     check_name  what is being checked
     result      the value in Snowflake right now
     expected    what it should be (section 1) or what Power BI showed (section 2)
   ===================================================================== */

USE ROLE SYSADMIN;          -- SYSADMIN inherits TRANSFORMER + REPORTER, so it can read every schema
USE WAREHOUSE GODESI_WH;

WITH
f   AS (SELECT * FROM GODESI_ANALYTICS.MARTS.FCT_ORDER_ITEMS),
d   AS (SELECT * FROM GODESI_ANALYTICS.MARTS.DIM_DATE),
p   AS (SELECT * FROM GODESI_ANALYTICS.MARTS.DIM_PRODUCTS),
c   AS (SELECT * FROM GODESI_ANALYTICS.MARTS.DIM_CHANNELS),
g   AS (SELECT * FROM GODESI_ANALYTICS.MARTS.DIM_GEOGRAPHY),
cu  AS (SELECT * FROM GODESI_ANALYTICS.MARTS.DIM_CUSTOMERS),
inv AS (SELECT * FROM GODESI_ANALYTICS.MARTS.MART_INVENTORY_HEALTH),

-- revenue by year, overall and by channel / region (for YoY checks)
yr AS (
    SELECT YEAR(order_date) AS y, SUM(net_revenue_inr) AS rev FROM f GROUP BY 1
),
ch_yoy AS (
    SELECT c.channel_name,
           SUM(IFF(YEAR(f.order_date) = 2025, f.net_revenue_inr, 0)) AS rev25,
           SUM(IFF(YEAR(f.order_date) = 2024, f.net_revenue_inr, 0)) AS rev24
    FROM f JOIN c ON f.channel = c.channel
    GROUP BY 1
),
rg_yoy AS (
    SELECT g.region,
           SUM(IFF(YEAR(f.order_date) = 2025, f.net_revenue_inr, 0)) AS rev25,
           SUM(IFF(YEAR(f.order_date) = 2024, f.net_revenue_inr, 0)) AS rev24
    FROM f JOIN g ON f.city = g.city
    GROUP BY 1
),
-- festival lift in 2025: average revenue per day, festival-season days vs other days
daily25 AS (
    SELECT d.date_day, d.is_festival_season, COALESCE(SUM(f.net_revenue_inr), 0) AS rev
    FROM d LEFT JOIN f ON f.order_date = d.date_day
    WHERE d.year = 2025
    GROUP BY 1, 2
),
-- Pareto: how many products are needed to reach 80% of revenue
prod_rev AS (
    SELECT p.product_name, SUM(f.net_revenue_inr) AS rev
    FROM f JOIN p ON f.sku_id = p.sku_id
    GROUP BY 1
),
pareto AS (
    SELECT product_name, rev,
           SUM(rev) OVER (ORDER BY rev DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(rev) OVER () AS cum_share
    FROM prod_rev
),
cat_rev AS (
    SELECT p.category, SUM(f.net_revenue_inr) AS rev
    FROM f JOIN p ON f.sku_id = p.sku_id
    GROUP BY 1
),
retention AS (
    SELECT months_since_first_order AS m, AVG(retention_pct) AS avg_ret
    FROM GODESI_ANALYTICS.MARTS.MART_CUSTOMER_COHORTS
    GROUP BY 1
)

/* ---------------- 1. Integrity: these must match "expected" ---------------- */
SELECT '1 Integrity' AS section, 'Duplicate sales_line_id in FCT_ORDER_ITEMS' AS check_name,
       TO_VARCHAR(COUNT(*) - COUNT(DISTINCT sales_line_id)) AS result, '0' AS expected FROM f
UNION ALL
SELECT '1 Integrity', 'Order lines missing a key (line, order, date, channel)',
       TO_VARCHAR(COUNT_IF(sales_line_id IS NULL OR order_id IS NULL OR order_date IS NULL OR channel IS NULL)), '0' FROM f
UNION ALL
SELECT '1 Integrity', 'Order date range',
       TO_VARCHAR(MIN(order_date)) || ' to ' || TO_VARCHAR(MAX(order_date)), '2024-01-01 to 2025-12-31' FROM f
UNION ALL
SELECT '1 Integrity', 'Order lines in FCT_ORDER_ITEMS', TO_VARCHAR(COUNT(*)), 'same as next row' FROM f
UNION ALL
SELECT '1 Integrity', 'Order lines in staging (website + marketplace + offline)',
       TO_VARCHAR( (SELECT COUNT(*) FROM GODESI_ANALYTICS.STAGING.STG_ECOM__ORDER_ITEMS)
                 + (SELECT COUNT(*) FROM GODESI_ANALYTICS.STAGING.STG_MARKETPLACE__ORDER_ITEMS)
                 + (SELECT COUNT(*) FROM GODESI_ANALYTICS.STAGING.STG_ERP__INVOICE_LINES) ),
       'same as previous row'
UNION ALL
SELECT '1 Integrity', 'Net revenue on cancelled lines (must be zero)',
       TO_VARCHAR(ROUND(SUM(IFF(is_cancelled, net_revenue_inr, 0)), 2)), '0' FROM f
UNION ALL
SELECT '1 Integrity', 'Profit rule broken (revenue - COGS - commission != profit), lines',
       TO_VARCHAR(COUNT_IF(ABS(net_revenue_inr - cogs_inr - commission_cost_inr - gross_profit_inr) > 0.01)), '0' FROM f
UNION ALL
SELECT '1 Integrity', 'FCT_ORDERS revenue = FCT_ORDER_ITEMS revenue',
       IFF(ABS((SELECT SUM(net_revenue_inr) FROM GODESI_ANALYTICS.MARTS.FCT_ORDERS) - SUM(net_revenue_inr)) < 1, 'equal', 'DIFFERENT'),
       'equal' FROM f
UNION ALL
SELECT '1 Integrity', 'Lines whose channel is not in DIM_CHANNELS',
       TO_VARCHAR(COUNT_IF(c.channel IS NULL)), '0' FROM f LEFT JOIN c ON f.channel = c.channel
UNION ALL
SELECT '1 Integrity', 'Lines whose city is not in DIM_GEOGRAPHY',
       TO_VARCHAR(COUNT_IF(g.city IS NULL)), '0' FROM f LEFT JOIN g ON f.city = g.city
UNION ALL
SELECT '1 Integrity', 'Lines whose SKU is not in DIM_PRODUCTS',
       TO_VARCHAR(COUNT_IF(p.sku_id IS NULL)), '0' FROM f LEFT JOIN p ON f.sku_id = p.sku_id
UNION ALL
SELECT '1 Integrity', 'Lines on an "Unknown product" (planted bad SKU)',
       TO_VARCHAR(COUNT_IF(p.category = 'Unknown')) || ' lines, SKU ' || COALESCE(LISTAGG(DISTINCT IFF(p.category = 'Unknown', f.sku_id, NULL), ', '), '-'),
       'a few lines, only GD-9999' FROM f LEFT JOIN p ON f.sku_id = p.sku_id
UNION ALL
SELECT '1 Integrity', 'Website lines whose customer is not in DIM_CUSTOMERS',
       TO_VARCHAR(COUNT_IF(cu.customer_id IS NULL)), '0'
FROM f LEFT JOIN cu ON f.customer_id = cu.customer_id WHERE f.channel = 'website'
UNION ALL
SELECT '1 Integrity', 'DIM_DATE days (rows / distinct)',
       TO_VARCHAR(COUNT(*)) || ' / ' || TO_VARCHAR(COUNT(DISTINCT date_day)), '731 / 731' FROM d
UNION ALL
SELECT '1 Integrity', 'DIM_PRODUCTS products (rows / distinct)',
       TO_VARCHAR(COUNT(*)) || ' / ' || TO_VARCHAR(COUNT(DISTINCT sku_id)), '41 / 41 (40 real + 1 Unknown)' FROM p
UNION ALL
SELECT '1 Integrity', 'MART_INVENTORY_HEALTH duplicate (date, SKU) rows',
       TO_VARCHAR(COUNT(*) - COUNT(DISTINCT snapshot_date, sku_id)), '0' FROM inv
UNION ALL
SELECT '1 Integrity', 'Dev and prod fact tables agree (lines / revenue)',
       IFF( (SELECT COUNT(*) FROM GODESI_ANALYTICS.DBT_DEV.FCT_ORDER_ITEMS) = COUNT(*)
        AND ABS((SELECT SUM(net_revenue_inr) FROM GODESI_ANALYTICS.DBT_DEV.FCT_ORDER_ITEMS) - SUM(net_revenue_inr)) < 1,
            'equal', 'DIFFERENT (dev not rebuilt - not a problem for the dashboard)'),
       'equal' FROM f

/* ---------------- 2. Dashboard numbers: compare with Power BI ---------------- */
UNION ALL
SELECT '2 Overview', 'Net Revenue, all time (INR)', TO_VARCHAR(ROUND(SUM(net_revenue_inr))), 'Power BI card: 61M' FROM f
UNION ALL
SELECT '2 Overview', 'Orders (not cancelled)', TO_VARCHAR(COUNT(DISTINCT IFF(NOT is_cancelled, order_id, NULL))), 'Power BI card: 84K' FROM f
UNION ALL
SELECT '2 Overview', 'AOV (INR)',
       TO_VARCHAR(ROUND(SUM(net_revenue_inr) / COUNT(DISTINCT IFF(NOT is_cancelled, order_id, NULL)), 2)), 'Power BI card: 727.51' FROM f
UNION ALL
SELECT '2 Overview', 'Net Revenue 2024 / 2025 (INR)',
       TO_VARCHAR(ROUND(MAX(IFF(y = 2024, rev, NULL)))) || ' / ' || TO_VARCHAR(ROUND(MAX(IFF(y = 2025, rev, NULL)))),
       '2025 LY in Power BI = 2024 value' FROM yr
UNION ALL
SELECT '2 Overview', 'Revenue YoY % 2025',
       TO_VARCHAR(ROUND((MAX(IFF(y = 2025, rev, NULL)) / MAX(IFF(y = 2024, rev, NULL)) - 1) * 100, 1)), 'Power BI: 101.3' FROM yr
UNION ALL
SELECT '2 Overview', 'Avg daily revenue 2025: festival season / other days',
       TO_VARCHAR(ROUND(AVG(IFF(is_festival_season, rev, NULL)))) || ' / ' || TO_VARCHAR(ROUND(AVG(IFF(NOT is_festival_season, rev, NULL)))),
       'Power BI: 29.2K / 19K (1.5x)' FROM daily25
UNION ALL
SELECT '2 Products', 'Products needed for 80% of revenue / products with sales',
       TO_VARCHAR(COUNT_IF(cum_share - rev / (SELECT SUM(rev) FROM prod_rev) < 0.8)) || ' / ' || TO_VARCHAR(COUNT(*)),
       'Power BI: 19 (Masala Peanuts crosses 80%)' FROM pareto
UNION ALL
SELECT '2 Products', 'Product where the running total crosses 80%',
       MIN_BY(product_name, cum_share), 'Power BI: Masala Peanuts' FROM pareto WHERE cum_share >= 0.8
UNION ALL
SELECT '2 Products', 'Top category by revenue', MAX_BY(category, rev), 'Power BI: Mithai' FROM cat_rev
UNION ALL
SELECT '2 Channels', 'Biggest channel by revenue', MAX_BY(channel_name, rev25 + rev24), 'Power BI: Distributors' FROM ch_yoy
UNION ALL
SELECT '2 Channels', 'Fastest-growing channel 2025 vs 2024',
       MAX_BY(channel_name || ' (' || TO_VARCHAR(ROUND((rev25 / NULLIF(rev24, 0) - 1) * 100, 1)) || '%)', rev25 / NULLIF(rev24, 0)),
       'Power BI: Zepto' FROM ch_yoy
UNION ALL
SELECT '2 Channels', 'Fastest-growing region 2025 vs 2024',
       MAX_BY(region || ' (' || TO_VARCHAR(ROUND((rev25 / NULLIF(rev24, 0) - 1) * 100, 1)) || '%)', rev25 / NULLIF(rev24, 0)),
       'Power BI: South' FROM rg_yoy
UNION ALL
SELECT '2 Customers', 'Website customers (ordered, not cancelled)',
       TO_VARCHAR(COUNT(DISTINCT IFF(channel = 'website' AND NOT is_cancelled, customer_id, NULL))), 'Power BI card: 10K' FROM f
UNION ALL
SELECT '2 Customers', 'One-time share: of all DIM_CUSTOMERS rows / of customers who ordered',
       TO_VARCHAR(ROUND(COUNT_IF(customer_segment = 'One-time') / COUNT(*) * 100, 2)) || '% / '
    || TO_VARCHAR(ROUND(COUNT_IF(customer_segment = 'One-time') / NULLIF(COUNT_IF(customer_segment <> 'Prospect'), 0) * 100, 2)) || '%',
       'Power BI donut: 59.01%' FROM cu
UNION ALL
SELECT '2 Customers', 'Avg retention %: month 1 / month 3',
       TO_VARCHAR(ROUND(MAX(IFF(m = 1, avg_ret, NULL)), 2)) || ' / ' || TO_VARCHAR(ROUND(MAX(IFF(m = 3, avg_ret, NULL)), 2)),
       'Power BI: 4.28 / 3.89' FROM retention
UNION ALL
SELECT '2 Promotions', 'Top promotion by revenue lift',
       MAX_BY(promo_name || ' (' || TO_VARCHAR(discount_pct) || '% off, lift ' || TO_VARCHAR(revenue_lift_pct) || '%)', revenue_lift_pct),
       'Power BI: 15% off, ~115% lift' FROM GODESI_ANALYTICS.MARTS.MART_PROMO_IMPACT
UNION ALL
SELECT '2 Inventory', 'Products on 31 Dec 2025: Stock-out / Low / Overstock',
       TO_VARCHAR(COUNT_IF(stock_status = 'Stock-out')) || ' / ' || TO_VARCHAR(COUNT_IF(stock_status = 'Low')) || ' / ' || TO_VARCHAR(COUNT_IF(stock_status = 'Overstock')),
       'Power BI: 1 / 0 / 3' FROM inv WHERE snapshot_date = '2025-12-31'
UNION ALL
SELECT '2 Inventory', 'Month with the most stock-out product-days',
       TO_VARCHAR(MAX_BY(mon, n)), 'Power BI: October'
FROM (SELECT MONTHNAME(snapshot_date) AS mon, COUNT_IF(stock_status = 'Stock-out') AS n FROM inv GROUP BY 1)

ORDER BY section, check_name;
