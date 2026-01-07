name: Manual Test Report — OneDrive Backup
about: Use this template to file a manual integration test report for OneDrive backup/restore flows
title: '[manual-test] OneDrive backup integration — {user_id} — {date}'
labels: qa, integration-test

---

**Tester:** @
**Date (UTC):** 
**Environment:** OS / Python / venv
**OneDrive client_id (redact if sensitive):**
**Test user id:** `user_001`

### Preconditions
- [ ] venv activated and Python version noted
- [ ] Local user state at `data/user_states/{user_id}`
- [ ] Encryption key present for user (or noted if testing missing-key)
- [ ] Token cache path defined for device flow testing

### Checklist & Results
For each step please mark PASS/FAIL and add short notes. Attach logs/screenshots.

1. OneDrive device flow authorization: PASS / FAIL — notes
2. Create local backup package: PASS / FAIL — notes
3. Inspect package for keys/tokens: PASS / FAIL — notes
4. Upload backup to OneDrive: PASS / FAIL — notes
5. Delete local data (simulate lost device): PASS / FAIL — notes
6. Download backup from OneDrive: PASS / FAIL — notes
7. Restore backup with key present: PASS / FAIL — notes
8. Sanity check boot & reasoning: PASS / FAIL — notes

### Failure scenarios
- Interrupted upload: PASS / FAIL — notes
- Expired device code: PASS / FAIL — notes
- Missing key: PASS / FAIL — notes
- Corrupted backup: PASS / FAIL — notes
- Wrong account/file: PASS / FAIL — notes

### Security & Privacy Checks
- Backup does NOT contain `.secret.key` (PASS / FAIL)
- Cloud file contains only encrypted blobs (PASS / FAIL)
- Tokens are not embedded in backups (PASS / FAIL)
- Restore without key does not reveal plaintext (PASS / FAIL)
- Safety checks blocked medical/medication suggestions post-restore (PASS / FAIL)

### Attachments
- Logs: 
- Screenshots:
- Notes:

---

Please @mention the reviewer and set the `qa` label when ready.