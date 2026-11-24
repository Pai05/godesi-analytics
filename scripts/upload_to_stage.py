"""Upload a local file (or a whole folder) to a Snowflake internal stage with PUT, then list the stage.

Logs in as DBT_USER with the key pair from Phase 1 and uses role LOADER
(granted to DBT_USER for Phase 2 by load/00_grant_loader_to_dbt_user.sql).

Usage (Git Bash, from the project root):
    export SNOWFLAKE_ACCOUNT=ORGNAME-ACCOUNTNAME
    .venv/Scripts/python.exe scripts/upload_to_stage.py data/raw/off_india_raw.tsv.gz @GODESI_RAW.OPEN_FOOD_FACTS.OFF_STAGE

You are asked for the private-key passphrase; it is never stored.
"""
import getpass
import os
import sys
from pathlib import Path

import snowflake.connector

KEY_FILE = Path.home() / ".ssh" / "snowflake" / "rsa_key.p8"


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    local_file = Path(sys.argv[1]).resolve()
    stage = sys.argv[2]
    if not local_file.exists():
        sys.exit(f"File or folder not found: {local_file}")
    if not KEY_FILE.is_file():
        sys.exit(f"Private key not found: {KEY_FILE}")

    account = os.environ.get("SNOWFLAKE_ACCOUNT") or input("Account identifier (ORGNAME-ACCOUNTNAME): ").strip()
    passphrase = getpass.getpass("Private key passphrase: ")

    conn = snowflake.connector.connect(
        account=account,
        user="DBT_USER",
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(KEY_FILE),
        private_key_password=passphrase,
        role="LOADER",
        warehouse="GODESI_WH",
    )
    try:
        cur = conn.cursor()
        print(f"Connected as {cur.execute('SELECT CURRENT_USER(), CURRENT_ROLE()').fetchone()}")

        # A single file goes to the stage root; a folder keeps its sub-folder layout
        # (data/raw/synthetic/batch_1/ecom/orders.csv.gz -> @stage/batch_1/ecom/orders.csv.gz).
        if local_file.is_dir():
            jobs = [(f, f"{stage}/{f.parent.relative_to(local_file).as_posix()}")
                    for f in sorted(local_file.rglob("*")) if f.is_file()]
        else:
            jobs = [(local_file, stage)]
        for f, target in jobs:
            put_sql = f"PUT 'file://{f.as_posix()}' {target} AUTO_COMPRESS = FALSE OVERWRITE = TRUE"
            for row in cur.execute(put_sql).fetchall():
                # source, target, source_size, target_size, source_compression, target_compression, status, message
                print(f"  {target}/{row[0]}: {row[6]} ({int(row[2]) / 1e6:.2f} MB) {row[7] or ''}")

        print(f"\nLIST {stage}")
        for row in cur.execute(f"LIST {stage}").fetchall():
            print(f"  {row[0]}  {int(row[1]):,} bytes")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
