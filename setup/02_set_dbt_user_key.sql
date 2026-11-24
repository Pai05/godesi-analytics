/* =====================================================================
   GoDesi Analytics — Phase 1: attach the public key to DBT_USER
   ---------------------------------------------------------------------
   1. Generate the key pair first (see setup/README.md, step 3).
   2. Paste the contents of rsa_key.pub below WITHOUT the
      "-----BEGIN PUBLIC KEY-----" / "-----END PUBLIC KEY-----" lines,
      as one line (remove the line breaks).
   3. Run in Snowsight.

   The PUBLIC key is safe to share. Never paste or commit the PRIVATE
   key (rsa_key.p8).
   ===================================================================== */

USE ROLE SECURITYADMIN;

ALTER USER DBT_USER SET RSA_PUBLIC_KEY = 'PASTE_PUBLIC_KEY_BODY_HERE';

-- Check: RSA_PUBLIC_KEY_FP should now show a SHA256 fingerprint
DESC USER DBT_USER;
