# OneDrive Backup Integration — Manual Testing Checklist & Guide

## 1. Purpose

Manual integration testing is necessary because unit tests and CI use mocks and cannot exercise interactive device authorization, human key transfer, real cloud uploads, or deliberate corruption and recovery scenarios. This guide documents step-by-step manual verification for OneDrive device-flow, backup creation/upload/download/restore, encryption key handling, failure and recovery scenarios, and safety assertions.

## 2. Preconditions

- OS: Windows / macOS / Linux supported. Examples use Windows paths; adjust for your environment.
- Python: Use the project virtual environment (tested with Python 3.10–3.11).
  - Activate venv (Windows PowerShell): `.\.venv\Scripts\Activate.ps1`
  - Confirm: `.venv\Scripts\python.exe --version`
- Environment variables: None required for the local flows. Keep `CLIENT_ID` handy for OneDrive.
- OneDrive app registration assumptions:
  - Registered public client app in Azure AD (native/public client).
  - Delegated Microsoft Graph scope `Files.ReadWrite` allowed.
  - `client_id` (app id) available to tester.
- Local key availability:
  - Each user must have the per-user symmetric key at `data/user_states/{user_id}/.secret.key` (secure file permissions).

---

## 3. OneDrive Device-Flow Test Checklist

1. Prepare test user and cache paths
   - Test user id example: `user_001` with local data in `data/user_states/user_001/`.
   - Token cache example path: `C:\Users\<you>\.nutrimama_onedrive_cache.json`.

2. Initiate the device flow
   - Option A (Python):
     ```py
     from app.onedrive_backup import authorize_device_flow
     authorize_device_flow(client_id="YOUR_CLIENT_ID", cache_path="C:\\Users\\you\\.nutrimama_onedrive_cache.json")
     ```
   - Option B (CLI):
     ```sh
     python scripts/onedrive_cli.py authorize --client-id YOUR_CLIENT_ID --cache C:\path\cache.json
     ```

3. Complete browser authorization
   - Visit the verification URL shown, enter the code, sign in with the test account, and consent to `Files.ReadWrite`.
   - Expected: `cache.json` is created and contains MSAL token cache JSON.

4. Verify token handling
   - Use `_load_app_from_cache` to confirm `acquire_token_silent` returns valid tokens if within TTL.
   - Confirm token cache only stores MSAL artifacts and is not embedded into backups.

5. Confirm no tokens or keys leak into backup
   - Create a backup package and inspect it for tokens or key material (search for `access_token`, `refresh_token`, `client_id`, and the secret key string).
   - Expected: backup contains metadata and base64-encoded encrypted blobs ONLY.

---

## 4. Backup & Restore Validation Steps

A. Create a backup package (local)

1. Ensure the user has the encryption key at `data/user_states/user_001/.secret.key`.
2. Generate package:
   ```py
   from app.storage import create_backup_package, save_backup_to_path
   bytes_pkg = create_backup_package("user_001")
   save_backup_to_path(bytes_pkg, "C:\\temp\\nutrimama_user_001_backup.json")
   ```
3. Expected: backup JSON exists and contains `version`, `user_id`, `created_at`, and `blobs` with base64-encoded encrypted data.

B. Upload to OneDrive

1. Upload via CLI or helper (example CLI):
   ```sh
   python scripts/onedrive_cli.py upload --client-id YOUR_CLIENT_ID --cache C:\path\cache.json --user user_001 --file C:\temp\nutrimama_user_001_backup.json
   ```
2. Expected: CLI prints success and returns a OneDrive file id.

C. Delete local data (simulate lost device)

1. Safely rename/move `data/user_states/user_001` to simulate deletion.
   - Confirm: encrypted DB and `.secret.key` are not present.
2. Expected: App reports missing local state for `user_001`.

D. Download & restore

1. Download backup using CLI:
   ```sh
   python scripts/onedrive_cli.py download --client-id YOUR_CLIENT_ID --cache C:\path\cache.json --file-id <FILE_ID> --out C:\temp\downloaded_backup.json
   ```
2. Expected: `downloaded_backup.json` exists and is a valid package.
3. Transfer encryption key securely to device, place at `data/user_states/user_001/.secret.key`.
4. Restore:
   ```py
   from app.storage import load_backup_package
   with open("C:\\temp\\downloaded_backup.json","rb") as f:
       load_backup_package("user_001", f.read())
   ```
5. Expected:
   - User `user_001` storage appears with encrypted blobs stored.
   - When the app loads with the key present, state and memory rehydrate correctly (actions, timestamps preserved).

E. Sanity checks

- Start app or run a smoke script to ensure the app can initialize and the reasoning engine behaves normally for `user_001`.
- Confirm safety checks don't trigger incorrectly after restore.

---

## 5. Failure Scenarios to Manually Test

1. Interrupted upload (network failure)
   - Simulate network interruption during upload and confirm:
     - Upload fails gracefully with error; partial file not accepted as a complete backup.
     - App does not delete local backup or mark it as uploaded.

2. Expired device code
   - Start device flow but do not complete within the allowed period.
   - Expected: device flow returns expiry; tester must re-run `authorize_device_flow`.

3. Missing encryption key on restore
   - Attempt to restore backup without `.secret.key` present.
   - Expected: encrypted blobs are written but decryption fails; clear error message indicates missing key; no plaintext data revealed.

4. Corrupted backup archive
   - Corrupt the JSON or base64 blob and attempt `load_backup_package`.
   - Expected: system detects corruption (JSON/base64 errors or validation failures) and refuses to write corrupted content.

5. Wrong OneDrive account / file mismatch
   - Verify that restoring a backup from a different user account does not auto-associate or overwrite a different local user without explicit confirmation.

6. Token cache misuse
   - Inspect token cache contents and ensure tokens are not embedded into backup. Deleting token cache should prevent token-based operations until reauthorization.

For each scenario, record test steps, observations, and logs.

---

## 6. Security & Privacy Assertions (must be verified)

- Backups never include encryption keys; confirm by inspecting backup JSON.
- Cloud provider stores only encrypted blobs; confirm by downloading and inspecting file content — it must be base64 encrypted data.
- No unsafe suggestions or medical recommendations are introduced during or after restore; run a reasoning check to confirm SafetyChecker enforces hard boundaries.
- Tokens remain in MSAL cache only, not in backups.
- Key transfer is performed securely by tester (platform keystore or secure transfer method). Document the method used.

---

## 7. Tester Sign-off Checklist

Mark each item PASS/FAIL and add notes:

- [ ] Completed OneDrive device flow and obtained token cache (PASS / FAIL: ___)
- [ ] Created a backup package and confirmed it contains only encrypted blobs (PASS / FAIL: ___)
- [ ] Uploaded backup to OneDrive and obtained file id (PASS / FAIL: ___)
- [ ] Removed local data and confirmed missing state without key (PASS / FAIL: ___)
- [ ] Transferred key securely and restored backup successfully (PASS / FAIL: ___)
- [ ] Corrupted backup test failed gracefully (PASS / FAIL: ___)
- [ ] Missing key test produced a clear error and did not leak data (PASS / FAIL: ___)
- [ ] Expired device code and interrupted upload handled with clear errors (PASS / FAIL: ___)
- [ ] Safety checks blocked any medical advice or medication suggestions post-restore (PASS / FAIL: ___)
- [ ] Confirmed that backups do not contain encryption keys or access tokens (PASS / FAIL: ___)

Attach logs, screenshots, and notes to this sign-off.

---

## Appendix: Quick Commands

- Create backup:
  ```py
  from app.storage import create_backup_package, save_backup_to_path
  save_backup_to_path(create_backup_package("user_001"), "C:\\temp\\nutrimama_user_001_backup.json")
  ```

- Upload (CLI):
  ```sh
  python scripts/onedrive_cli.py upload --client-id YOUR_CLIENT_ID --cache C:\path\cache.json --user user_001 --file C:\temp\nutrimama_user_001_backup.json
  ```

- Download (CLI):
  ```sh
  python scripts/onedrive_cli.py download --client-id YOUR_CLIENT_ID --cache C:\path\cache.json --file-id <FILE_ID> --out C:\temp\downloaded_backup.json
  ```

- Authorize device flow (CLI):
  ```sh
  python scripts/onedrive_cli.py authorize --client-id YOUR_CLIENT_ID --cache C:\path\cache.json
  ```

- Restore:
  ```py
  from app.storage import load_backup_package
  with open("C:\\temp\\downloaded_backup.json","rb") as f:
      load_backup_package("user_001", f.read())
  ```

---

If you'd like, I can also add a simple "Manual Test Report" template file that QA can fill out and attach to PRs or release notes. Do you want that as a follow-up? (Yes/No)