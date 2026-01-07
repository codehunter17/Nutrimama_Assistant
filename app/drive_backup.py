"""Google Drive backup helpers for Nutrimama.

This module uses the OAuth installed-app flow (browser) to let a user
authorize access to their Drive and upload/download backup packages.

Note: imports for Google libraries are done lazily inside functions so
the core app can run even if the google libs are not installed.
"""
from typing import Optional
import os
import io
import logging

LOGGER = logging.getLogger(__name__)


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def authorize_with_browser(client_secrets_path: str, creds_store_path: str) -> None:
    """Run an installed-app OAuth flow in the browser and save credentials.

    Args:
        client_secrets_path: path to OAuth client_secrets.json obtained from
            Google Cloud Console.
        creds_store_path: path where to store serialized credentials (JSON).
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        import google.auth.transport.requests
        import json

        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save credentials
        with open(creds_store_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        LOGGER.info("Saved Google Drive credentials to %s", creds_store_path)
    except Exception:
        LOGGER.exception("Failed to run Google OAuth flow. Make sure client_secrets.json is valid.")


def _load_creds(creds_store_path: str):
    # Lazy import to avoid hard dependency on module import
    from google.oauth2.credentials import Credentials

    if not os.path.exists(creds_store_path):
        raise FileNotFoundError("Credentials not found; run authorize first")

    import json

    data = json.load(open(creds_store_path, "r", encoding="utf-8"))
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    return creds


def upload_backup_to_drive(user_id: str, creds_store_path: str, file_name: Optional[str] = None) -> Optional[str]:
    """Upload the user's backup package to Google Drive and return file id.

    This reads encrypted blobs from the local DB and uploads them as a single
    file named `nutrimama_{user_id}_backup.json` by default.
    """
    try:
        from googleapiclient.http import MediaIoBaseUpload
        from googleapiclient.discovery import build

        # create package bytes using storage helper to avoid duplication
        from app.storage import create_backup_package

        package = create_backup_package(user_id)
        creds = _load_creds(creds_store_path)
        service = build("drive", "v3", credentials=creds)

        name = file_name or f"nutrimama_{user_id}_backup.json"
        fh = io.BytesIO(package)
        media = MediaIoBaseUpload(fh, mimetype="application/json")

        file_metadata = {"name": name}
        res = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = res.get("id")
        LOGGER.info("Uploaded backup to Drive: %s (id=%s)", name, file_id)
        return file_id
    except Exception:
        LOGGER.exception("Failed to upload backup to Google Drive")
        return None


def download_backup_from_drive(file_id: str, creds_store_path: str) -> Optional[bytes]:
    """Download a backup file by Drive `file_id` and return bytes.

    Caller should pass the bytes to `load_backup_package` to restore.
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        creds = _load_creds(creds_store_path)
        service = build("drive", "v3", credentials=creds)

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        data = fh.read()
        LOGGER.info("Downloaded backup file id=%s (%d bytes)", file_id, len(data))
        return data
    except Exception:
        LOGGER.exception("Failed to download backup from Google Drive")
        return None
