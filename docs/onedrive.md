# OneDrive Backup Integration

🔧 Overview

This document explains how to use the OneDrive backup helpers provided in `app/onedrive_backup.py` to store and retrieve user backup packages using Microsoft OneDrive via the Microsoft Graph API.

## Features

- Device-code flow authorization via MSAL (`authorize_device_flow`) for public client apps
- Upload a portable encrypted backup package with `upload_backup_to_onedrive`
- Download a backup package with `download_backup_from_onedrive`

## Quick start

1. Create or register a public app in Azure AD and note the `client_id` (application id). Configure the app to allow delegated `Files.ReadWrite` scope for Microsoft Graph.
2. On the machine where you want to authorize, run:

```python
from app.onedrive_backup import authorize_device_flow

client_id = "YOUR_CLIENT_ID"
cache_path = "~/.nutrimama_onedrive_cache.json"
authorize_device_flow(client_id, cache_path)
```

The function prints a verification URL and code. Visit the URL, enter the code, sign in, and consent.

3. Upload a backup package (assumes encryption key already present in the target device keystore):

```python
from app.onedrive_backup import upload_backup_to_onedrive

fid = upload_backup_to_onedrive(user_id="user_001", client_id=client_id, cache_path=cache_path, file_name="nutrimama_backup.json")
```

4. Download a backup by ID:

```python
from app.onedrive_backup import download_backup_from_onedrive

data = download_backup_from_onedrive(file_id=fid, client_id=client_id, cache_path=cache_path)
```

## Security & Privacy Notes 🔒

- Backup packages are portable byte blobs that do NOT include the per-user encryption key. The recipient device MUST have the correct key available in its secure keystore to decrypt the package.
- Do not store the encryption key in the same cloud storage as your backups. Use secure platform keystore mechanisms or a separate secret management system when transferring keys between devices.
- The device-code flow requires user interaction and explicit consent — it is **designed for user-driven authorization**, not for unattended server-to-server setups.

## Testing & Troubleshooting

- Unit tests mock MSAL and network requests; to do a real integration test you must provide a `client_id` and run the device flow to obtain tokens.
- If `upload_backup_to_onedrive` raises `RuntimeError("No token available; please run authorize_device_flow first")`, the token cache is empty or expired — re-run `authorize_device_flow`.

---

If you'd like, I can add an example GitHub Actions workflow that runs a manual OneDrive integration step (note: interactive device flow cannot be used in CI, so integration tests should remain manual or be mocked).