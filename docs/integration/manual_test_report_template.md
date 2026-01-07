# Manual Test Report — OneDrive Backup Integration

Use this template to record results from a single manual integration test run. Attach logs, screenshots, and any related artifacts.

---

## Report metadata
- Tester: ____________________
- Date (UTC): __________________
- Environment (OS / Python / venv): __________________
- OneDrive `client_id` used (redact if sensitive): __________________
- Test user id: __________________ (e.g., `user_001`)

---

## Preconditions
- [ ] Project venv activated and Python version noted above
- [ ] Local user state exists at `data/user_states/{user_id}`
- [ ] Encryption key present at `data/user_states/{user_id}/.secret.key` (or note if testing missing-key scenario)
- [ ] Token cache path defined for device flow testing

Notes:


---

## Test Steps & Results
For each step mark PASS / FAIL and add brief notes. Attach logs/screenshots.

1) OneDrive Device Flow Authorization
- Command/run: __________________
- Result: PASS / FAIL
- Notes:

2) Create local backup package
- Command/run: `create_backup_package("{user_id}")`
- Result: PASS / FAIL
- Notes:

3) Inspect backup package for keys/tokens
- Result: PASS / FAIL
- Notes:

4) Upload backup to OneDrive
- Command/run: __________________
- File id / URL: __________________
- Result: PASS / FAIL
- Notes:

5) Delete/move local user data (simulate lost device)
- Action performed: __________________
- Result: PASS / FAIL
- Notes:

6) Download backup from OneDrive
- Command/run: __________________
- Result: PASS / FAIL
- Notes:

7) Restore backup with key present
- Command/run: `load_backup_package("{user_id}", bytes)`
- Result: PASS / FAIL
- Notes:

8) Sanity check app boot and reasoning cycle
- Command/run: `python -m app.main` (or smoke script)
- Observed behavior: __________________
- Result: PASS / FAIL
- Notes:

---

## Failure Scenario Tests
List each scenario tested with outcome.

- Interrupted upload: PASS / FAIL — Notes:
- Expired device code: PASS / FAIL — Notes:
- Missing encryption key on restore: PASS / FAIL — Notes:
- Corrupted backup archive: PASS / FAIL — Notes:
- Wrong account / file mismatch: PASS / FAIL — Notes:

---

## Security & Privacy Checks (must PASS)
- Backup does NOT contain `.secret.key` (PASS / FAIL)
- Cloud file contains only encrypted blobs (PASS / FAIL)
- Tokens are not embedded in backups (PASS / FAIL)
- Restore without key does not reveal plaintext (PASS / FAIL)
- Safety checks blocked any medical/medication suggestions post-restore (PASS / FAIL)

Notes/Evidence (attach logs/screenshots):


---

## Overall Assessment
- Overall result: PASS / FAIL
- Summary notes:


---

## Sign-off
- Tester signature: ____________________
- Reviewer (if applicable): ____________________
- Date (UTC): __________________


---

Attach logs: `logs/` or inline snippets. Ensure any sensitive tokens are redacted when publishing reports.
