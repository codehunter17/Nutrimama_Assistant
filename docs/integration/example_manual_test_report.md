# Example Manual Test Report — OneDrive Backup Integration

- Tester: QA Engineer
- Date (UTC): 2026-01-08
- Environment: Windows 11 / Python 3.11 / .venv
- OneDrive client_id: (redacted)
- Test user id: user_001

---

## Preconditions
- venv activated
- `data/user_states/user_001/` exists
- encryption key at `data/user_states/user_001/.secret.key`
- token cache path: `C:\Users\qa\.nutrimama_onedrive_cache.json`

---

## Results
1) OneDrive Device Flow Authorization
- Command: `python scripts/onedrive_cli.py authorize --client-id <redacted> --cache C:\Users\qa\.nutrimama_onedrive_cache.json`
- Result: PASS
- Notes: Device code flow completed in browser; cache file created (redacted tokens).

2) Create local backup package
- Command: `python -c "from app.storage import create_backup_package, save_backup_to_path; save_backup_to_path(create_backup_package('user_001'), 'C:\\temp\\nutrimama_user_001_backup.json')"`
- Result: PASS
- Notes: Backup JSON contains `version`, `user_id`, and `blobs` with base64 strings.

3) Inspect backup package for keys/tokens
- Result: PASS
- Notes: No `access_token`, `refresh_token`, or key contents in backup.

4) Upload backup to OneDrive
- Command: `python scripts/onedrive_cli.py upload --client-id <redacted> --cache C:\Users\qa\.nutrimama_onedrive_cache.json --user user_001 --file C:\temp\nutrimama_user_001_backup.json`
- File id: `01ABCD...`
- Result: PASS
- Notes: Upload returned file id.

5) Delete/move local user data
- Action: Renamed `data/user_states/user_001` to `data/user_states/user_001.deleted`
- Result: PASS
- Notes: App reports missing local state for user_001.

6) Download backup from OneDrive
- Command: `python scripts/onedrive_cli.py download --client-id <redacted> --cache C:\Users\qa\.nutrimama_onedrive_cache.json --file-id 01ABCD --out C:\temp\downloaded_backup.json`
- Result: PASS
- Notes: File downloaded and checksum matched local upload.

7) Restore backup with key present
- Action: Restored `.secret.key` to `data/user_states/user_001/.secret.key` using secure transfer
- Command: `python -c "from app.storage import load_backup_package; load_backup_package('user_001', open('C:\\temp\\downloaded_backup.json','rb').read())"`
- Result: PASS
- Notes: Storage DB created and decrypted successfully; memory actions present.

8) Sanity check app boot and reasoning cycle
- Command: `python -m app.main`
- Observed: App initialized; user_001 state loaded; reasoning engine did not propose medical or unsafe suggestions.
- Result: PASS

---

## Failure Scenarios
- Interrupted upload: Simulated network drop; app returned upload error and did not delete local backup — PASS
- Expired device code: Initiated device flow and delayed entry until expiry; MSAL returned expiry; required re-run — PASS
- Missing key on restore: Attempted restore without key; app wrote encrypted blobs but decryption failed with clear error — PASS
- Corrupted backup: Truncated the JSON; `load_backup_package` failed with parse error and refused to write — PASS
- Wrong account: Downloaded backup with file id on different account; restoration proceeded only after explicit confirmation of user id — PASS

---

## Security & Privacy Checks
- Backup does NOT contain `.secret.key` — PASS
- Cloud file contains only encrypted blobs — PASS
- Tokens are not embedded in backups — PASS
- Restore without key does not reveal plaintext — PASS
- Safety checks blocked any medical/medication suggestions post-restore — PASS

---

## Overall Assessment
- Overall result: PASS
- Summary notes: Integration flow behaves as expected; document the token cache path and keep key transfer instructions in secure procedure.

---

## Sign-off
- Tester signature: QA Engineer
- Reviewer: Team Lead
- Date (UTC): 2026-01-08


(Attach logs and screenshots to this report when filing.)