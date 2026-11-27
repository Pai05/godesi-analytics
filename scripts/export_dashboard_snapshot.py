"""Export the dbt marts the Streamlit app reads into Parquet files, for the public copy of the app.

The public app (Streamlit Community Cloud) cannot log in to Snowflake, so it reads this snapshot
with DuckDB instead and runs the same SQL on it. Only the columns the app uses are exported, and no
customer details beyond the synthetic customer_id.

Usage (Git Bash, from the project root; asks for the account identifier and key passphrase):
    .venv/Scripts/python.exe scripts/export_dashboard_snapshot.py

Writes dashboard/data_snapshot/<table>.parquet. Re-run after a prod build to refresh the snapshot.
"""
import getpass
import os
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "data_snapshot"
KEY_FILE = Path.home() / ".ssh" / "snowflake" / "rsa_key.p8"

# table -> columns the app needs ("*" = whole table; these marts are already aggregated)
TABLES = {
    "FCT_ORDERS": "order_date, channel, customer_id, is_cancelled, net_revenue_inr, gross_profit_inr",
    "DIM_CHANNELS": "*",
    "DIM_CUSTOMERS": "customer_id, cohort_month, customer_segment",
    "DIM_DATE": "date_day, festival_name",
    "MART_SALES_DAILY": "*",
    "MART_PRODUCT_PERFORMANCE": "*",
    "MART_CHANNEL_PERFORMANCE": "*",
    "MART_CUSTOMER_COHORTS": "*",
    "MART_INVENTORY_HEALTH": "*",
    "MART_PROMO_IMPACT": "*",
    "MART_MARKET_LANDSCAPE": "*",
}


def main() -> None:
    account = os.environ.get("SNOWFLAKE_ACCOUNT") or input("Account identifier (ORGNAME-ACCOUNTNAME): ").strip()
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or getpass.getpass("Private key passphrase: ")
    conn = snowflake.connector.connect(
        account=account, user="DBT_USER", authenticator="SNOWFLAKE_JWT",
        private_key_file=str(KEY_FILE), private_key_password=passphrase,
        role="TRANSFORMER", warehouse="GODESI_WH", database="GODESI_ANALYTICS", schema="MARTS",
    )
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        cur = conn.cursor()
        for table, columns in TABLES.items():
            cur.execute(f"select {columns} from GODESI_ANALYTICS.MARTS.{table}")
            df = cur.fetch_pandas_all()
            path = OUT / f"{table.lower()}.parquet"
            df.to_parquet(path, index=False)
            print(f"  {table:<26} {len(df):>8,} rows  {path.stat().st_size / 1024:>7,.0f} KB -> {path.relative_to(ROOT)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
