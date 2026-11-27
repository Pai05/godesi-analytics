/* =====================================================================
   GoDesi Analytics — Phase 7: a separate key for GitHub Actions
   ---------------------------------------------------------------------
   DBT_USER can hold two public keys. Slot 1 = your laptop (Phase 1),
   slot 2 = GitHub Actions. If the CI key ever leaks, unset slot 2 and
   your own key keeps working:
       ALTER USER DBT_USER UNSET RSA_PUBLIC_KEY_2;

   1. Make the key pair in Git Bash (see the Phase 7 steps).
   2. Paste rsa_ci.pub below WITHOUT the BEGIN/END lines, as one line.
   3. Run in Snowsight.
   The PUBLIC key is safe to share. Never paste or commit rsa_ci.p8.
   ===================================================================== */

USE ROLE SECURITYADMIN;

ALTER USER DBT_USER SET RSA_PUBLIC_KEY_2 = 'PASTE_CI_PUBLIC_KEY_HERE';

-- Check: RSA_PUBLIC_KEY_FP and RSA_PUBLIC_KEY_2_FP both show a SHA256 fingerprint
DESC USER DBT_USER;

-- Cost check: credits used per day by GODESI_WH (CI runs are tagged dbt_ci,
-- the scheduled build dbt_prod_scheduled)
USE ROLE ACCOUNTADMIN;
SELECT TO_DATE(start_time) AS day, ROUND(SUM(credits_used), 3) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE warehouse_name = 'GODESI_WH'
GROUP BY 1 ORDER BY 1 DESC
LIMIT 14;
