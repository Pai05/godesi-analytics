/* =====================================================================
   GoDesi Analytics — Phase 1: verification
   ---------------------------------------------------------------------
   Run statement by statement in Snowsight. Expected results are in
   the comments. Steps marked "SHOULD FAIL" prove the permissions are
   tight — an error there is the correct outcome.
   ===================================================================== */

-- 1. Objects exist --------------------------------------------------------
USE ROLE SYSADMIN;
SHOW WAREHOUSES LIKE 'GODESI_WH';           -- size X-Small, auto_suspend 60, resource_monitor GODESI_RM
SHOW SCHEMAS IN DATABASE GODESI_RAW;        -- ERP, ECOM, MARKETPLACE, INVENTORY, OPEN_FOOD_FACTS (+ INFORMATION_SCHEMA, PUBLIC)
SHOW SCHEMAS IN DATABASE GODESI_ANALYTICS;  -- DBT_DEV, STAGING, INTERMEDIATE, MARTS, SNAPSHOTS owned by TRANSFORMER

-- 2. Grants look right ----------------------------------------------------
SHOW GRANTS TO ROLE LOADER;
SHOW GRANTS TO ROLE TRANSFORMER;
SHOW GRANTS TO ROLE REPORTER;
SHOW FUTURE GRANTS IN DATABASE GODESI_RAW;
SHOW FUTURE GRANTS IN SCHEMA GODESI_ANALYTICS.MARTS;
SHOW GRANTS TO USER DBT_USER;               -- TRANSFORMER

-- 3. LOADER can write RAW -------------------------------------------------
USE ROLE LOADER;
USE WAREHOUSE GODESI_WH;
CREATE OR REPLACE TABLE GODESI_RAW.ERP._PERMISSION_TEST (id INT);  -- succeeds
INSERT INTO GODESI_RAW.ERP._PERMISSION_TEST VALUES (1);

-- 4. TRANSFORMER reads RAW, writes ANALYTICS, cannot write RAW -----------
USE ROLE TRANSFORMER;
SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE();                        -- TRANSFORMER, GODESI_WH
SELECT * FROM GODESI_RAW.ERP._PERMISSION_TEST;                     -- returns 1 row (future grant worked)
CREATE OR REPLACE TABLE GODESI_ANALYTICS.MARTS._PERMISSION_TEST AS SELECT 1 AS id;  -- succeeds
CREATE OR REPLACE TABLE GODESI_RAW.ERP._SHOULD_FAIL (id INT);      -- SHOULD FAIL: insufficient privileges

-- 5. REPORTER reads MARTS only ------------------------------------------
USE ROLE REPORTER;
SELECT * FROM GODESI_ANALYTICS.MARTS._PERMISSION_TEST;             -- returns 1 row (future grant worked)
SELECT * FROM GODESI_RAW.ERP._PERMISSION_TEST;                     -- SHOULD FAIL: does not exist or not authorized

-- 6. Clean up -------------------------------------------------------------
USE ROLE TRANSFORMER;
DROP TABLE IF EXISTS GODESI_ANALYTICS.MARTS._PERMISSION_TEST;
USE ROLE LOADER;
DROP TABLE IF EXISTS GODESI_RAW.ERP._PERMISSION_TEST;

-- 7. Resource monitor (ACCOUNTADMIN only) ---------------------------------
USE ROLE ACCOUNTADMIN;
SHOW RESOURCE MONITORS LIKE 'GODESI_RM';    -- credit_quota 20, frequency MONTHLY
USE ROLE SYSADMIN;
