/* =====================================================================
   GoDesi Analytics — Phase 1: Snowflake setup
   ---------------------------------------------------------------------
   Run this whole worksheet in Snowsight as your own (admin) user.
   It is safe to re-run: every statement is idempotent.

   Creates:
     Warehouse  GODESI_WH          X-Small, auto-suspend 60 s
     Database   GODESI_RAW         raw data, loaded by role LOADER
     Database   GODESI_ANALYTICS   everything dbt builds (role TRANSFORMER)
     Roles      LOADER, TRANSFORMER, REPORTER
     User       DBT_USER           service user for dbt (key-pair auth)
     Monitor    GODESI_RM          20 credits / month, suspends at 90-100 %
   ===================================================================== */


/* ---------------------------------------------------------------------
   1. Compute and storage  (SYSADMIN owns objects)
   --------------------------------------------------------------------- */
USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS GODESI_WH
  WAREHOUSE_SIZE      = 'XSMALL'
  AUTO_SUSPEND        = 60          -- seconds idle before it stops billing
  AUTO_RESUME         = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT             = 'GoDesi analytics: loading, dbt and BI';

-- Raw layer: one schema per source system
CREATE DATABASE IF NOT EXISTS GODESI_RAW
  COMMENT = 'Untouched source data. Written by LOADER, read by TRANSFORMER.';

CREATE SCHEMA IF NOT EXISTS GODESI_RAW.ERP             COMMENT = 'Products, distributors, stores, promotions (synthetic)';
CREATE SCHEMA IF NOT EXISTS GODESI_RAW.ECOM            COMMENT = 'D2C website customers, orders, returns (synthetic)';
CREATE SCHEMA IF NOT EXISTS GODESI_RAW.MARKETPLACE     COMMENT = 'Amazon / Flipkart / quick-commerce orders (synthetic)';
CREATE SCHEMA IF NOT EXISTS GODESI_RAW.INVENTORY       COMMENT = 'Daily stock snapshots (synthetic)';
CREATE SCHEMA IF NOT EXISTS GODESI_RAW.OPEN_FOOD_FACTS COMMENT = 'Real Open Food Facts India product extract (ODbL)';

-- Analytics layer: dbt writes here
CREATE DATABASE IF NOT EXISTS GODESI_ANALYTICS
  COMMENT = 'Models built by dbt. Written by TRANSFORMER, MARTS read by REPORTER.';

CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.DBT_DEV      COMMENT = 'Personal development sandbox (dbt target dev)';
CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.STAGING      COMMENT = 'Prod: cleaned 1:1 source models';
CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.INTERMEDIATE COMMENT = 'Prod: joined / enriched models';
CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.MARTS        COMMENT = 'Prod: star schema and business marts';
CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.SNAPSHOTS    COMMENT = 'Prod: dbt snapshots (SCD type 2)';


/* ---------------------------------------------------------------------
   2. Roles  (SECURITYADMIN manages roles and grants)
   --------------------------------------------------------------------- */
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS LOADER      COMMENT = 'Loads files into GODESI_RAW';
CREATE ROLE IF NOT EXISTS TRANSFORMER COMMENT = 'dbt: reads GODESI_RAW, builds GODESI_ANALYTICS';
CREATE ROLE IF NOT EXISTS REPORTER    COMMENT = 'BI tools: read-only on GODESI_ANALYTICS.MARTS';

-- Role hierarchy: custom roles roll up to SYSADMIN so admins can see everything
GRANT ROLE LOADER      TO ROLE SYSADMIN;
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE REPORTER    TO ROLE SYSADMIN;

-- Let you (the person running this script) switch into each role.
-- Your signup user is owned by ACCOUNTADMIN, so other roles may not "see" it:
-- run these three grants as ACCOUNTADMIN.
USE ROLE ACCOUNTADMIN;
-- Wrap the name in double quotes so it matches exactly (signup user names
-- can be stored in lowercase, which an unquoted name would not match).
SET my_user = '"' || CURRENT_USER() || '"';
GRANT ROLE LOADER      TO USER IDENTIFIER($my_user);
GRANT ROLE TRANSFORMER TO USER IDENTIFIER($my_user);
GRANT ROLE REPORTER    TO USER IDENTIFIER($my_user);
USE ROLE SECURITYADMIN;


/* ---------------------------------------------------------------------
   3. Warehouse access
   --------------------------------------------------------------------- */
GRANT USAGE ON WAREHOUSE GODESI_WH TO ROLE LOADER;
GRANT USAGE ON WAREHOUSE GODESI_WH TO ROLE TRANSFORMER;
GRANT USAGE ON WAREHOUSE GODESI_WH TO ROLE REPORTER;


/* ---------------------------------------------------------------------
   4. LOADER: create stages, file formats and tables in GODESI_RAW
   --------------------------------------------------------------------- */
GRANT USAGE ON DATABASE GODESI_RAW TO ROLE LOADER;
GRANT USAGE, CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
  ON ALL SCHEMAS IN DATABASE GODESI_RAW TO ROLE LOADER;
GRANT USAGE, CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
  ON FUTURE SCHEMAS IN DATABASE GODESI_RAW TO ROLE LOADER;


/* ---------------------------------------------------------------------
   5. TRANSFORMER: read everything in GODESI_RAW ...
   --------------------------------------------------------------------- */
GRANT USAGE  ON DATABASE GODESI_RAW                      TO ROLE TRANSFORMER;
GRANT USAGE  ON ALL SCHEMAS    IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;
GRANT USAGE  ON FUTURE SCHEMAS IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;
GRANT SELECT ON ALL TABLES     IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE TABLES  IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;
GRANT SELECT ON ALL VIEWS      IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE VIEWS   IN DATABASE GODESI_RAW    TO ROLE TRANSFORMER;

/* ... and own the analytics schemas, so dbt can create / replace models.
   CREATE SCHEMA lets dbt make extra schemas (e.g. CI_PR_<n> in Phase 7). */
GRANT USAGE, CREATE SCHEMA ON DATABASE GODESI_ANALYTICS TO ROLE TRANSFORMER;

GRANT OWNERSHIP ON SCHEMA GODESI_ANALYTICS.DBT_DEV      TO ROLE TRANSFORMER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA GODESI_ANALYTICS.STAGING      TO ROLE TRANSFORMER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA GODESI_ANALYTICS.INTERMEDIATE TO ROLE TRANSFORMER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA GODESI_ANALYTICS.MARTS        TO ROLE TRANSFORMER COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA GODESI_ANALYTICS.SNAPSHOTS    TO ROLE TRANSFORMER COPY CURRENT GRANTS;


/* ---------------------------------------------------------------------
   6. REPORTER: read-only on MARTS (current and future tables / views)
   --------------------------------------------------------------------- */
GRANT USAGE  ON DATABASE GODESI_ANALYTICS                       TO ROLE REPORTER;
GRANT USAGE  ON SCHEMA   GODESI_ANALYTICS.MARTS                 TO ROLE REPORTER;
GRANT SELECT ON ALL TABLES    IN SCHEMA GODESI_ANALYTICS.MARTS  TO ROLE REPORTER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GODESI_ANALYTICS.MARTS  TO ROLE REPORTER;
GRANT SELECT ON ALL VIEWS     IN SCHEMA GODESI_ANALYTICS.MARTS  TO ROLE REPORTER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA GODESI_ANALYTICS.MARTS  TO ROLE REPORTER;


/* ---------------------------------------------------------------------
   7. Service user for dbt  (public key is added by 02_set_dbt_user_key.sql)
   --------------------------------------------------------------------- */
CREATE USER IF NOT EXISTS DBT_USER
  TYPE              = SERVICE       -- no password, key-pair login only
  DEFAULT_ROLE      = TRANSFORMER
  DEFAULT_WAREHOUSE = GODESI_WH
  DEFAULT_NAMESPACE = GODESI_ANALYTICS.DBT_DEV
  COMMENT           = 'dbt Core / dbt Cloud / CI service user';

GRANT ROLE TRANSFORMER TO USER DBT_USER;


/* ---------------------------------------------------------------------
   8. Cost guard-rail  (resource monitors need ACCOUNTADMIN)
   --------------------------------------------------------------------- */
USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS GODESI_RM
  WITH CREDIT_QUOTA    = 20
       FREQUENCY       = MONTHLY
       START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75  PERCENT DO NOTIFY
           ON 90  PERCENT DO SUSPEND            -- finish running queries, then stop
           ON 100 PERCENT DO SUSPEND_IMMEDIATE; -- cancel running queries

ALTER WAREHOUSE GODESI_WH SET RESOURCE_MONITOR = GODESI_RM;

-- Your own defaults: log in as SYSADMIN (not ACCOUNTADMIN) with GODESI_WH
ALTER USER IDENTIFIER($my_user) SET DEFAULT_ROLE = SYSADMIN, DEFAULT_WAREHOUSE = GODESI_WH;

-- Done. Switch back to a non-admin role for daily work.
USE ROLE SYSADMIN;
