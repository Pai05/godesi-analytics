/* =====================================================================
   GoDesi Analytics — Phase 2: let DBT_USER act as LOADER (temporary)
   ---------------------------------------------------------------------
   The upload script (scripts/upload_to_stage.py) logs in as DBT_USER with
   your key pair and switches to role LOADER to PUT files into stages.

   At the END of Phase 2, run the REVOKE at the bottom so DBT_USER goes back
   to TRANSFORMER only (dbt should never write raw data).
   ===================================================================== */

USE ROLE SECURITYADMIN;
GRANT ROLE LOADER TO USER DBT_USER;

SHOW GRANTS TO USER DBT_USER;   -- expect LOADER and TRANSFORMER


-- ---- End of Phase 2: run this ----
-- USE ROLE SECURITYADMIN;
-- REVOKE ROLE LOADER FROM USER DBT_USER;
