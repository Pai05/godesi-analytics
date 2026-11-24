# Phase 1 — Snowflake setup

Goal: one X-Small warehouse, a RAW and an ANALYTICS database, three roles, a `DBT_USER`
for dbt, and a 20-credit monthly cost cap. Takes about 30 minutes.

## What gets built

| Object | Name | Purpose |
| --- | --- | --- |
| Warehouse | `GODESI_WH` | X-Small, auto-suspend 60 s |
| Database | `GODESI_RAW` | Schemas `ERP`, `ECOM`, `MARKETPLACE`, `INVENTORY`, `OPEN_FOOD_FACTS` |
| Database | `GODESI_ANALYTICS` | Schemas `DBT_DEV`, `STAGING`, `INTERMEDIATE`, `MARTS`, `SNAPSHOTS` |
| Role | `LOADER` | Writes to RAW (you, in Phase 2) |
| Role | `TRANSFORMER` | Reads RAW, owns ANALYTICS schemas (dbt) |
| Role | `REPORTER` | Reads MARTS only (BI tool) |
| User | `DBT_USER` | Service user, key-pair login, role `TRANSFORMER` |
| Resource monitor | `GODESI_RM` | 20 credits / month: notify 75 %, suspend 90 %, kill 100 % |

```
ACCOUNTADMIN
 ├── SECURITYADMIN ── USERADMIN
 └── SYSADMIN
      ├── LOADER       → GODESI_RAW (write)
      ├── TRANSFORMER  → GODESI_RAW (read), GODESI_ANALYTICS (own)
      └── REPORTER     → GODESI_ANALYTICS.MARTS (read)
```

## Steps

### 1. Create the Snowflake trial account
1. Sign up at signup.snowflake.com — 30 days, about $400 of free credits.
2. Edition: **Enterprise** (more features to learn, same trial credits).
3. Cloud / region: **AWS — Asia Pacific (Mumbai)**.
4. Verify your email (needed for resource-monitor alerts) and log in to Snowsight.
5. Note your **account identifier**: bottom-left menu → your account → *Copy account identifier*.
   It looks like `ORGNAME-ACCOUNTNAME`. dbt needs it in Phase 3.

### 2. Run the setup script
1. Snowsight → **Projects → Worksheets → + SQL Worksheet**.
2. Paste all of `01_snowflake_setup.sql`.
3. Run all (Ctrl+Shift+Enter). Every statement should say *successfully*.
   The script is idempotent — re-running it is safe.

### 3. Generate the key pair for `DBT_USER`
Run in **Git Bash** (openssl is already installed there). Keys go in your home folder,
**not** in the project folder:

```bash
mkdir -p ~/.ssh/snowflake && cd ~/.ssh/snowflake

# Private key (encrypted; you will be asked for a passphrase — remember it)
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes-256-cbc -inform PEM -out rsa_key.p8

# Public key
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# Print the public key body as one line, ready to paste
grep -v "PUBLIC KEY" rsa_key.pub | tr -d '\n'; echo
```

Private key path for Phase 3: `C:\Users\<you>\.ssh\snowflake\rsa_key.p8`.

### 4. Attach the public key
1. Open `02_set_dbt_user_key.sql` in a new worksheet.
2. Replace `PASTE_PUBLIC_KEY_BODY_HERE` with the one-line output from step 3.
3. Run it. `DESC USER DBT_USER` should show a value in `RSA_PUBLIC_KEY_FP`.

Paste the key only in the Snowsight worksheet; the repo file keeps the placeholder.

### 5. Verify
Run `03_verify_setup.sql` **statement by statement** (Ctrl+Enter) and compare with the comments.
Two statements are marked *SHOULD FAIL* — getting an error on those is the correct result.

The real login test for `DBT_USER` happens in Phase 3 with `dbt debug`.

## Done when
- [ ] `01_snowflake_setup.sql` runs cleanly twice in a row
- [ ] `DBT_USER` has an RSA public key fingerprint
- [ ] Every line of `03_verify_setup.sql` gives the expected result
- [ ] Account identifier and private key path noted for Phase 3

## Concepts to read about while you do this
- **Storage vs compute**: databases cost storage; warehouses cost credits only while running.
- **Credits**: X-Small = 1 credit/hour, billed per second with a 60-second minimum.
- **RBAC**: privileges go to roles, roles go to users. Custom roles roll up to `SYSADMIN`.
- **Future grants**: `GRANT ... ON FUTURE TABLES` covers tables that don't exist yet —
  that is why dbt's new tables are readable by `REPORTER` automatically.
- **System roles**: `ACCOUNTADMIN` (everything — use rarely), `SECURITYADMIN` (grants),
  `USERADMIN` (users/roles), `SYSADMIN` (objects).

## Troubleshooting
| Error | Fix |
| --- | --- |
| `Insufficient privileges to operate on account` at the resource monitor | Your user lacks `ACCOUNTADMIN`. On a trial, the signup user has it — log in as that user. |
| `SQL compilation error` near `TYPE = SERVICE` | Delete the `TYPE = SERVICE` line and re-run. |
| `Schema ... does not exist or not authorized` in the verify script | Re-run `01_snowflake_setup.sql`. |
| `User '<NAME>' does not exist or not authorized` | 1) Use `USE ROLE ACCOUNTADMIN;` before any `GRANT ... TO USER` or `ALTER USER`. 2) Run `SELECT CURRENT_USER();` — if the name is lowercase or differs from your login, write it in double quotes exactly as shown, e.g. `ALTER USER "myusername" ...`. |
| Forgot the key passphrase | Generate a new key pair and re-run `02_set_dbt_user_key.sql`. |
