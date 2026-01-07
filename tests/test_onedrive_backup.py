import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import json
import tempfile
from unittest.mock import MagicMock

import app.onedrive_backup as od


class DummyApp:
    def __init__(self, token=None):
        self._token = token or {"access_token": "fake-token"}
        self._cache = MagicMock()

    def get_accounts(self):
        return ["acct"]

    def acquire_token_silent(self, scopes, account=None):
        return self._token

    def token_cache_serialize(self):
        return "{}"


def test_upload_calls_graph(monkeypatch, tmp_path):
    # Create dummy cache file
    cache = tmp_path / "cache.json"
    cache.write_text("{}")

    # Mock _load_app_from_cache to return DummyApp
    monkeypatch.setattr(od, "_load_app_from_cache", lambda client_id, cache_path: (DummyApp(), None))

    # Avoid reading actual DB; mock package generation
    monkeypatch.setattr("app.storage.get_backup_bytes_for_mobile", lambda uid: b'{"dummy": true}')

    # Mock requests.put
    class DummyResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "file123"}

    monkeypatch.setattr("requests.put", lambda url, headers, data: DummyResp())

    # Now call upload
    fid = od.upload_backup_to_onedrive("user_a", "cliid", str(cache), "backup.json")
    assert fid == "file123"


def test_download_calls_graph(monkeypatch, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("{}")

    monkeypatch.setattr(od, "_load_app_from_cache", lambda client_id, cache_path: (DummyApp(), None))

    class DummyResp:
        def raise_for_status(self):
            pass

        @property
        def content(self):
            return b"backup-binary"

    monkeypatch.setattr("requests.get", lambda url, headers, stream=True: DummyResp())

    data = od.download_backup_from_onedrive("file123", "cliid", str(cache))
    assert data == b"backup-binary"
