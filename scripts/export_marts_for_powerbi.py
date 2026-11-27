"""Plan B for Power BI: export the dbt marts to CSV files.

Use this only if Power BI cannot log in to Snowflake directly (for example because
your account requires multi-factor authentication). Logs in as DBT_USER with the
key pair from Phase 1, reads GODESI_ANALYTICS.MARTS and writes data/powerbi/*.csv.

Usage (Git Bash, from the project root):
    .venv/Scripts/python.exe scripts/export_marts_for_powerbi.py

Asks for the account identifier (unless SNOWFLAKE_ACCOUNT is set) and the key passphrase.
"""
import csv
import getpass
import os
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "powerbi"
KEY_FILE = Path.home() / ".ssh" / "snowflake" / "rsa_key.p8"
TABLES = [
    "FCT_ORDER_ITEMS", "DIM_DATE", "DIM_PRODUCTS", "DIM_CHANNELS", "DIM_GEOGRAPHY", "DIM_CUSTOMERS",
    "MART_CUSTOMER_COHORTS", "MART_PROMO_IMPACT", "MART_INVENTORY_HEALTH", "MART_MARKET_LANDSCAPE",
]


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
        for table in TABLES:
            cur.execute(f"select * from GODESI_ANALYTICS.MARTS.{table}")
            header = [c[0] for c in cur.description]
            path = OUT / f"{table.lower()}.csv"
            rows = 0
            with path.open("w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Power BI reads ₹ correctly
                writer = csv.writer(f)
                writer.writerow(header)
                for batch in iter(lambda: cur.fetchmany(10_000), []):
                    writer.writerows(batch)
                    rows += len(batch)
            print(f"  {table:<26} {rows:>8,} rows -> {path.relative_to(ROOT)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
