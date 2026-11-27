/* =====================================================================
   GoDesi Analytics — Phase 6: home for the Streamlit dashboard
   ---------------------------------------------------------------------
   Creates GODESI_ANALYTICS.APPS and lets REPORTER create a Streamlit app
   there. The app runs with its owner's role (REPORTER), so it can read
   the MARTS and nothing else. Run in a Snowflake worksheet. Safe to re-run.
   ===================================================================== */

USE ROLE SYSADMIN;
CREATE SCHEMA IF NOT EXISTS GODESI_ANALYTICS.APPS
  COMMENT = 'Streamlit apps and other dashboard objects';

USE ROLE SECURITYADMIN;
GRANT USAGE                ON SCHEMA GODESI_ANALYTICS.APPS TO ROLE REPORTER;
GRANT CREATE STREAMLIT     ON SCHEMA GODESI_ANALYTICS.APPS TO ROLE REPORTER;
GRANT CREATE STAGE         ON SCHEMA GODESI_ANALYTICS.APPS TO ROLE REPORTER;  -- Snowsight stores the app files in a stage

-- Check: REPORTER should list USAGE, CREATE STREAMLIT and CREATE STAGE on APPS
SHOW GRANTS TO ROLE REPORTER;

USE ROLE SYSADMIN;
