# Prepare a Git Bash session for dbt. Run it with "source", not "bash":
#
#     cd /d/go_desi
#     source scripts/dbt_env.sh
#
# Asks for the key passphrase (kept only in this terminal's memory, never saved),
# activates the Python environment and moves you into the dbt project folder.
# Tip: add  export SNOWFLAKE_ACCOUNT=ORGNAME-ACCOUNTNAME  to ~/.bashrc to skip that question.

if [ -z "$SNOWFLAKE_ACCOUNT" ]; then
    read -r -p "Snowflake account identifier (ORGNAME-ACCOUNTNAME): " SNOWFLAKE_ACCOUNT
fi
read -r -s -p "Private key passphrase: " SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
echo
export SNOWFLAKE_ACCOUNT SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
export SNOWFLAKE_PRIVATE_KEY_PATH="$(cygpath -w "$HOME/.ssh/snowflake/rsa_key.p8")"

source /d/go_desi/.venv/Scripts/activate
cd /d/go_desi/godesi || return
echo "Ready: dbt $(dbt --version 2>/dev/null | sed -n 's/.*installed: *//p' | head -1), account $SNOWFLAKE_ACCOUNT, folder $(pwd)"
