/* =====================================================================
   GoDesi Analytics — Phase 6b: read-only service user for Power BI
   ---------------------------------------------------------------------
   Power BI connects through the Snowflake ODBC driver with key-pair login
   (no password needed). This user can only use REPORTER = read the MARTS.

   1. Generate the key pair first (dashboard/POWER_BI_GUIDE.md, Option C).
   2. Paste the public key body below (one line, no BEGIN/END lines).
   3. Run in a Snowflake worksheet.
   ===================================================================== */

USE ROLE SECURITYADMIN;

CREATE USER IF NOT EXISTS POWERBI_USER
  TYPE              = SERVICE
  DEFAULT_ROLE      = REPORTER
  DEFAULT_WAREHOUSE = GODESI_WH
  DEFAULT_NAMESPACE = GODESI_ANALYTICS.MARTS
  COMMENT           = 'Power BI Desktop via ODBC, read-only (REPORTER)';

GRANT ROLE REPORTER TO USER POWERBI_USER;

ALTER USER POWERBI_USER SET RSA_PUBLIC_KEY = 'PASTE_POWERBI_PUBLIC_KEY_HERE';

-- Check: RSA_PUBLIC_KEY_FP shows SHA256:...  and DEFAULT_ROLE = REPORTER
DESC USER POWERBI_USER;
