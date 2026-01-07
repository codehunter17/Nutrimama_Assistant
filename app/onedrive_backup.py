"""OneDrive backup helpers using MSAL and Microsoft Graph.

Provides device-code flow authorization and simple upload/download helpers.
Imports are lazy so the core app can run without MSAL installed.
"""
from typing import Optional
import os
import io
import json
import logging

LOGGER = logging.getLogger(__name__)

# Graph endpoints
GRAPH_UPLOAD_URL = "https://graph.microsoft.com/v1.0/me/drive/root:/{}:/content"
GRAPH_DOWNLOAD_BY_ID = "https://graph.microsoft.com/v1.0/me/drive/items/{}/content"


def authorize_device_flow(client_id: str, cache_path: str, scopes=None, authority: str = "https://login.microsoftonline.com/common") -> None:
    """Run device-code flow and store token cache to `cache_path`.

    Args:
        client_id: MSAL application (public client) id
        cache_path: path to write token cache JSON
        scopes: list of scopes, default is Files.ReadWrite
    """
    scopes = scopes or ["Files.ReadWrite"]
    try:
        import msal
    except Exception:
        LOGGER.exception("MSAL not installed; please `pip install msal` to use OneDrive")
        raise

    app = msal.PublicClientApplication(client_id, authority=authority)
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError("Failed to start device flow")

    print("To authorize, visit:", flow["verification_uri"])
    print("Enter code:", flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)  # blocks until complete
    if "access_token" in result:
        # Save cache
        cache = app.token_cache.serialize()
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(cache)
        LOGGER.info("Saved MSAL token cache to %s", cache_path)
    else:
        LOGGER.error("Device flow failed: %s", result)
        raise RuntimeError("Device flow failed")


def _load_app_from_cache(client_id: str, cache_path: str, authority: str = "https://login.microsoftonline.com/common"):
    try:
        import msal
    except Exception:
        LOGGER.exception("MSAL not installed")
        raise

    cache = msal.SerializableTokenCache()
    if os.path.exists(cache_path):
        cache.deserialize(open(cache_path, "r", encoding="utf-8").read())

    app = msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)
    return app, cache


def upload_backup_to_onedrive(user_id: str, client_id: str, cache_path: str, file_name: Optional[str] = None) -> Optional[str]:
    """Upload backup package to the user's OneDrive and return the file id (or None).

    This will load the package bytes via `app.storage.get_backup_bytes_for_mobile`.
    """
    try:
        import requests
        from app.storage import get_backup_bytes_for_mobile
    except Exception:
        LOGGER.exception("Missing dependencies for OneDrive upload (msal/requests)")
        raise

    app, cache = _load_app_from_cache(client_id, cache_path)

    # Acquire token silently
    scopes = ["Files.ReadWrite"]
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result:
        LOGGER.info("No valid token in cache; interactive device flow required")
        raise RuntimeError("No token available; please run authorize_device_flow first")

    access_token = result.get("access_token")
    if not access_token:
        LOGGER.error("No access token available")
        return None

    package = get_backup_bytes_for_mobile(user_id)
    name = file_name or f"nutrimama_{user_id}_backup.json"
    url = GRAPH_UPLOAD_URL.format(name)

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        resp = requests.put(url, headers=headers, data=package)
        resp.raise_for_status()
        data = resp.json()
        file_id = data.get("id") or data.get("name")
        LOGGER.info("Uploaded backup to OneDrive: %s (id=%s)", name, file_id)
        return file_id
    except Exception:
        LOGGER.exception("Failed to upload to OneDrive")
        return None


def download_backup_from_onedrive(file_id: str, client_id: str, cache_path: str) -> Optional[bytes]:
    try:
        import requests
    except Exception:
        LOGGER.exception("Missing requests library")
        raise

    app, _ = _load_app_from_cache(client_id, cache_path)
    scopes = ["Files.ReadWrite"]
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    if not result or not result.get("access_token"):
        LOGGER.error("No token available; please authorize first")
        return None

    access_token = result.get("access_token")
    url = GRAPH_DOWNLOAD_BY_ID.format(file_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()
        return resp.content
    except Exception:
        LOGGER.exception("Failed to download from OneDrive")
        return None
