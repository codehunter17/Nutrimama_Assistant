# Backup & Restore (Local-first + Mobile)

This document describes Nutrimama's backup and restore flow.

Goals:
- Local-first storage (encrypted) on the user's device.
- Portable encrypted backup packages that users can upload to their own cloud (Google Drive, OneDrive, iCloud).
- Central backups are opt-in and disabled by default.

Key design points:

- Encryption: local data is encrypted with a per-user symmetric key stored at `data/user_states/{user_id}/.secret.key`. The encrypted blobs themselves are stored in `storage.db`.
- Backup package: `create_backup_package(user_id)` returns a JSON bytes package containing base64-encoded encrypted blobs (it does NOT include the key).
- Restore: `load_backup_package(user_id, package_bytes)` writes encrypted blobs into the user's DB; decryption will succeed only if the device has the corresponding `.secret.key`.

CLI helpers:

- `scripts/drive_cli.py` — authorize, upload, download with Google Drive (uses `app/drive_backup.py`).
- `scripts/onedrive_cli.py` — authorize, upload, download with OneDrive (uses `app/onedrive_backup.py`).

For more detail on OneDrive usage and device flow, see `docs/onedrive.md`.

Typical mobile flow:

1. App creates local encrypted storage with `save_user_state`.
2. User chooses to back up: app calls `get_backup_bytes_for_mobile(user_id)` and uploads the returned bytes to their cloud provider.
3. To restore on another device, the user must transfer the `.secret.key` into the OS secure keystore of the new device (or use the app's secure key transfer flow). Then app calls `load_backup_package(user_id, package_bytes)` to restore encrypted blobs.

Security considerations:

- The backup package without the key is safe to store in user cloud: attacker cannot decrypt it without the key.
- Key transfer between devices MUST be done securely (QR code + ephemeral TLS, or platform keystore sync). Do not email keys or store them in plain text.
- For added security, consider storing the encryption key in platform keystores (Android Keystore, iOS Keychain, Windows DPAPI) and never persisting the raw key in files on shared storage.

Testing:

- Automated tests in `tests/test_backup_flow.py` exercise backup package creation, save-to-path, and restore cycle (copying the `.secret.key` to simulate a key-bearing device).
