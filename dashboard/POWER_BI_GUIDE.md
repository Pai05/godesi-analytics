# Phase 6b — GoDesi dashboard in Power BI Desktop

Goal: a 5-page Power BI report on the same dbt marts as the Streamlit app, built the way
analysts do it at work: **import → data model (star schema) → DAX measures → report pages**.
Time: 3–5 hours spread over a few sessions.

---

## Part 1 — Install (10 min)

1. Open the **Microsoft Store** on Windows, search **Power BI Desktop**, click **Get** (free).
2. Open it. If it asks you to sign in, close that box — you do not need an account to build reports.
3. **File → Options and settings → Options → Regional Settings**: set *Locale for import* to
   **English (India)** so dates and ₹ amounts read correctly.

---

## Part 2 — Get the data

### Option A: connect directly to Snowflake (try this first)

1. **Home → Get data → More… → Database → Snowflake → Connect.**
2. Fill in:
   | Field | Value |
   | --- | --- |
   | Server | your account identifier + `.snowflakecomputing.com`, e.g. `abcdefg-xy12345.snowflakecomputing.com` |
   | Warehouse | `GODESI_WH` |
   | Advanced options → Role name | `REPORTER` |
   | Data Connectivity mode | **Import** |
3. Click **OK**. Choose the **Snowflake** tab, enter your Snowflake **login name** and **password**, click **Connect**.
4. In the Navigator, expand **GODESI_ANALYTICS → MARTS** and tick these 10 tables:
   `FCT_ORDER_ITEMS, DIM_DATE, DIM_PRODUCTS, DIM_CHANNELS, DIM_GEOGRAPHY, DIM_CUSTOMERS,
   MART_CUSTOMER_COHORTS, MART_PROMO_IMPACT, MART_INVENTORY_HEALTH, MART_MARKET_LANDSCAPE`
5. Click **Load**. About 250,000 rows in total; takes under a minute.

**If login fails** (MFA prompt, "multi-factor authentication required", "authentication failed"): use Option B.

### Option C: direct connection with key pair, via ODBC (use this if you sign in to Snowflake with Google)

1. **Key for Power BI** (Git Bash, no passphrase — the user is read-only):
   ```bash
   cd ~/.ssh/snowflake
   openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -inform PEM -out rsa_powerbi.p8
   openssl rsa -in rsa_powerbi.p8 -pubout -out rsa_powerbi.pub
   grep -v "PUBLIC KEY" rsa_powerbi.pub | tr -d '\n' | clip
   ```
2. **Snowflake:** run `setup/05_powerbi_user.sql` with the public key pasted in (creates `POWERBI_USER`, role REPORTER).
3. **Install the 64-bit Snowflake ODBC driver** (`snowflake-odbc-<version>.x86_64.msi`), then restart Power BI.
   Version 4.x registers as **`Snowflake ODBC`**; older 3.x as `SnowflakeDSIIDriver`.
4. **Power BI: Get data → ODBC → DSN (None) → Advanced options → Connection string:**
   ```
   driver={Snowflake ODBC};server=<identifier>.snowflakecomputing.com;authenticator=SNOWFLAKE_JWT;priv_key_file=C:\Users\<you>\.ssh\snowflake\rsa_powerbi.p8;role=REPORTER;warehouse=GODESI_WH;database=GODESI_ANALYTICS;schema=MARTS
   ```
   (Do not put `uid=` in the string — Power BI rejects it.)
5. Credentials window → **Database** → user `POWERBI_USER`, password: any placeholder → **Connect**.
6. Tick the 10 tables under GODESI_ANALYTICS → MARTS → **Load**. Refresh later with **Home → Refresh**.

### Option B: CSV export (works always)

1. **Git Bash:**
   ```bash
   cd /d/go_desi
   .venv/Scripts/python.exe scripts/export_marts_for_powerbi.py
   ```
   Enter account identifier and key passphrase. Expect 10 lines like
   `FCT_ORDER_ITEMS  165,xxx rows -> data\powerbi\fct_order_items.csv`.
2. **Power BI: Home → Get data → Text/CSV**, pick `D:\go_desi\data\powerbi\fct_order_items.csv` → **Load**.
   Repeat for the other 9 files.
3. Rename each table to its upper-case mart name (double-click the table name in the Data pane),
   e.g. `fct_order_items` → `FCT_ORDER_ITEMS`, so the DAX below works as written.

To refresh later: re-run the script, then **Home → Refresh** in Power BI.

---

## Part 3 — Check data types (Power Query, 10 min)

**Home → Transform data** opens Power Query. For each table, click the icon left of a column
name to set its type:

| Columns | Type |
| --- | --- |
| `ORDER_DATE`, `DATE_DAY`, `MONTH_START`, `COHORT_MONTH`, `SNAPSHOT_DATE`, `START_DATE`, `END_DATE`, `FIRST_ORDER_DATE` | **Date** |
| all `*_INR`, `*_PCT`, `QUANTITY`, `DAYS_OF_COVER`, `ON_HAND_UNITS` | **Decimal number** |
| `IS_CANCELLED`, `IS_RETURNED`, `IS_FESTIVAL_SEASON`, `IS_GODESI` | **True/False** |

Option A usually gets these right already. Click **Close & Apply**.

---

## Part 4 — Build the data model (15 min)

Click the **Model view** icon (left bar, third icon). Drag a column onto the matching column
to create each relationship. All are **many-to-one (\*:1), single direction**:

| From (many) | To (one) |
| --- | --- |
| `FCT_ORDER_ITEMS[ORDER_DATE]` | `DIM_DATE[DATE_DAY]` |
| `FCT_ORDER_ITEMS[SKU_ID]` | `DIM_PRODUCTS[SKU_ID]` |
| `FCT_ORDER_ITEMS[CHANNEL]` | `DIM_CHANNELS[CHANNEL]` |
| `FCT_ORDER_ITEMS[CITY]` | `DIM_GEOGRAPHY[CITY]` |
| `FCT_ORDER_ITEMS[CUSTOMER_ID]` | `DIM_CUSTOMERS[CUSTOMER_ID]` |
| `MART_INVENTORY_HEALTH[SNAPSHOT_DATE]` | `DIM_DATE[DATE_DAY]` |
| `MART_INVENTORY_HEALTH[SKU_ID]` | `DIM_PRODUCTS[SKU_ID]` |

Delete any other relationship Power BI created automatically. `MART_CUSTOMER_COHORTS`,
`MART_PROMO_IMPACT` and `MART_MARKET_LANDSCAPE` stay unconnected (they are already summarised).

**Mark the date table:** select `DIM_DATE` → **Table tools → Mark as date table** → column `DATE_DAY`.
This is what makes "same period last year" work.

**Sort month names:** select `DIM_DATE[MONTH_NAME]` → **Column tools → Sort by column → MONTH**.

You have just rebuilt your dbt star schema inside Power BI — the fact table in the middle,
dimensions around it.

---

## Part 5 — DAX measures (30 min)

Create a home for measures: **Home → Enter data** → name the table `_Measures` → **Load**.
Then for each measure: select `_Measures` → **Home → New measure** → paste → Enter.
Set the format in **Measure tools** (₹ currency, % or whole number) as noted.

```dax
Net Revenue = SUM ( FCT_ORDER_ITEMS[NET_REVENUE_INR] )                       -- ₹, 0 decimals

Gross Profit = SUM ( FCT_ORDER_ITEMS[GROSS_PROFIT_INR] )                     -- ₹

Gross Margin % = DIVIDE ( [Gross Profit], [Net Revenue] )                    -- %

Orders =
CALCULATE (
    DISTINCTCOUNT ( FCT_ORDER_ITEMS[ORDER_ID] ),
    FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE ()
)                                                                            -- whole number

AOV = DIVIDE ( [Net Revenue], [Orders] )                                     -- ₹

Units Sold =
CALCULATE (
    SUM ( FCT_ORDER_ITEMS[QUANTITY] ),
    FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE (),
    FCT_ORDER_ITEMS[IS_RETURNED] = FALSE ()
)

Discount % =
DIVIDE (
    CALCULATE ( SUM ( FCT_ORDER_ITEMS[DISCOUNT_INR] ), FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE () ),
    CALCULATE ( SUM ( FCT_ORDER_ITEMS[GROSS_AMOUNT_INR] ), FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE () )
)                                                                            -- %

Return Rate % =
DIVIDE (
    CALCULATE ( COUNTROWS ( FCT_ORDER_ITEMS ), FCT_ORDER_ITEMS[IS_RETURNED] = TRUE () ),
    CALCULATE ( COUNTROWS ( FCT_ORDER_ITEMS ), FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE () )
)                                                                            -- %

-- Latest year in the current selection vs the year before it. Works with the Year slicer cleared
-- (SAMEPERIODLASTYEAR would then compare 2024+2025 with 2024 alone and show 100%+).
Net Revenue CY = CALCULATE ( [Net Revenue], DIM_DATE[YEAR] = MAX ( DIM_DATE[YEAR] ) )

Net Revenue LY = CALCULATE ( [Net Revenue], DIM_DATE[YEAR] = MAX ( DIM_DATE[YEAR] ) - 1 )

Revenue YoY % = DIVIDE ( [Net Revenue CY] - [Net Revenue LY], [Net Revenue LY] )   -- %

Revenue Share % = DIVIDE ( [Net Revenue], CALCULATE ( [Net Revenue], ALL ( DIM_CHANNELS ) ) )   -- %

Avg Daily Revenue = AVERAGEX ( VALUES ( DIM_DATE[DATE_DAY] ), [Net Revenue] )  -- ₹

Website Customers =
CALCULATE (
    DISTINCTCOUNT ( FCT_ORDER_ITEMS[CUSTOMER_ID] ),
    FCT_ORDER_ITEMS[CHANNEL] = "website",
    FCT_ORDER_ITEMS[IS_CANCELLED] = FALSE ()
)

Cumulative Revenue % =
VAR CurrentRevenue = [Net Revenue]
VAR AllProducts =
    ADDCOLUMNS ( ALLSELECTED ( DIM_PRODUCTS[PRODUCT_NAME] ), "@rev", [Net Revenue] )
RETURN
    DIVIDE (
        SUMX ( FILTER ( AllProducts, [@rev] >= CurrentRevenue ), [@rev] ),
        SUMX ( AllProducts, [@rev] )
    )                                                                        -- %

Products Out of Stock =
CALCULATE (
    DISTINCTCOUNT ( MART_INVENTORY_HEALTH[SKU_ID] ),
    MART_INVENTORY_HEALTH[STOCK_STATUS] = "Stock-out",
    LASTDATE ( DIM_DATE[DATE_DAY] )
)
```

What to learn here: **CALCULATE** changes the filter context, **time intelligence**
(`SAMEPERIODLASTYEAR`) needs a marked date table, and **ALL / ALLSELECTED** remove filters
for share-of-total and running-total maths.

---

## Part 6 — Report pages

Click **Report view** (top icon on the left bar). Create 5 pages (the **+** at the bottom).
On every page: a title text box that states the **finding**, not just the topic
(e.g. "Quick commerce doubled in 2025" rather than "Channels").

Add two slicers to page 1, then **View → Sync slicers** to show them on all sales pages:
- `DIM_DATE[YEAR]` (style: Tile)
- `DIM_CHANNELS[CHANNEL_TYPE]` (style: Dropdown)

### Page 1 — Executive overview
| Visual | Fields |
| --- | --- |
| 5 × **Card** (new card visual) | Net Revenue · Revenue YoY % · Orders · AOV · Gross Margin % |
| **Stacked column chart** | X: `DIM_DATE[MONTH_START]` · Y: Net Revenue · Legend: `DIM_CHANNELS[CHANNEL_TYPE]` |
| **Line chart** | X: `DIM_DATE[MONTH_NAME]` · Y: Net Revenue, Net Revenue LY |
| **Clustered bar** | Y: `DIM_DATE[IS_FESTIVAL_SEASON]` · X: Avg Daily Revenue (shows the festival lift) |

### Page 2 — Products
| Visual | Fields / settings |
| --- | --- |
| **Bar chart**, Top 10 | Y: `DIM_PRODUCTS[PRODUCT_NAME]` · X: Net Revenue · Filters pane → Product name → *Top N* = 10 by Net Revenue |
| **Line and clustered column** (Pareto) | X: `PRODUCT_NAME` sorted by Net Revenue descending · Columns: Net Revenue · Line: Cumulative Revenue % |
| **Scatter chart** | Values: `DIM_PRODUCTS[CATEGORY]` · X: Net Revenue · Y: Gross Margin % · Size: Units Sold |
| **Matrix** | Rows: CATEGORY → PRODUCT_NAME · Values: Net Revenue, Gross Margin %, Units Sold |

### Page 3 — Channels & regions
| Visual | Fields / settings |
| --- | --- |
| **Matrix** (scorecard) | Rows: `DIM_CHANNELS[CHANNEL_NAME]` · Values: Net Revenue, Revenue Share %, Orders, AOV, Discount %, Return Rate %, Gross Margin %, Revenue YoY % · Format → Cell elements → **Data bars** on Net Revenue, **Background color** on Revenue YoY % |
| **100% stacked area** | X: `DIM_DATE[MONTH_START]` · Y: Net Revenue · Legend: CHANNEL_NAME |
| **Clustered bar** | Y: `DIM_GEOGRAPHY[REGION]` · X: Revenue YoY % |
| *(optional)* **Map** | Location: `DIM_GEOGRAPHY[CITY]` · Bubble size: Net Revenue (enable maps in Options → Security if asked) |

### Page 4 — Customers
| Visual | Fields / settings |
| --- | --- |
| **Matrix** (cohort heatmap) | Rows: `MART_CUSTOMER_COHORTS[COHORT_MONTH]` · Columns: `MONTHS_SINCE_FIRST_ORDER` · Values: `RETENTION_PCT` (Average) · Format → Cell elements → **Background color** → gradient white → dark blue. Filter `MONTHS_SINCE_FIRST_ORDER` ≤ 12 |
| **Line chart** | X: `MONTHS_SINCE_FIRST_ORDER` · Y: average of `RETENTION_PCT` |
| **Donut** | Legend: `DIM_CUSTOMERS[CUSTOMER_SEGMENT]` · Values: Count of CUSTOMER_ID |
| **Card** | Website Customers |

### Page 5 — Promotions & inventory
| Visual | Fields / settings |
| --- | --- |
| **Bar chart** | Y: `MART_PROMO_IMPACT[PROMO_NAME]` · X: `REVENUE_LIFT_PCT` (Sum) · sorted descending |
| **Table** | PROMO_CODE, PROMO_CHANNEL, DISCOUNT_PCT, AVG_DAILY_REVENUE_BEFORE, AVG_DAILY_REVENUE_DURING, REVENUE_LIFT_PCT |
| **100% stacked area** | X: `DIM_DATE[MONTH_START]` · Y: Count of `MART_INVENTORY_HEALTH[SKU_ID]` · Legend: `STOCK_STATUS` (colours: Stock-out red, Low orange, Healthy green, Overstock purple) |
| **Table** (products needing action) | PRODUCT_NAME, STOCK_STATUS, ON_HAND_UNITS, AVG_DAILY_UNITS_28D, DAYS_OF_COVER · filter SNAPSHOT_DATE = 31-12-2025 and STOCK_STATUS is not Healthy |
| **Card** | Products Out of Stock |

Optional 6th page — **Market (real data)**: scatter of `MART_MARKET_LANDSCAPE`
(X: `MEDIAN_SUGARS_100G`, Y: `PCT_NUTRISCORE_D_OR_E`, Size: `PRODUCTS`, Legend: `IS_GODESI`, Details: `BRAND_NAME`).

---

## Part 7 — Polish (30 min)

- **View → Themes**: pick one theme and keep colours consistent (same colour = same channel on every page).
- Align visuals: select several → **Format → Align**.
- **Tooltips**: on charts, drag Gross Margin % and Orders into the *Tooltips* well.
- **Drill-through**: on Page 2 add `DIM_PRODUCTS[PRODUCT_NAME]` to *Drill through* — right-clicking a product anywhere jumps to its page.
- Hide technical columns (keys, `UPDATED_AT`) in the Data pane: right-click → **Hide in report view**.

Save as `D:\go_desi\dashboard\GoDesi_Sales.pbix` (the file holds a copy of the data, so it is
kept out of Git).

---

## Done when

- [ ] 10 tables loaded, 7 relationships, DIM_DATE marked as date table
- [ ] All 15 measures created and formatted
- [ ] 5 pages built, slicers synced, every page title states a finding
- [ ] Numbers match the Streamlit app for the same filters (e.g. Net Revenue for 2025, all channels)

The last check is real analyst practice: two tools on the same dbt marts must agree.
