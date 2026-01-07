"""Pluggable persistence for Nutrimama.

Default: local encrypted SQLite per-user (local-first). Optionally backups
to Google Drive (user-controlled) when `ENABLE_GOOGLE_DRIVE_BACKUP` is set
and service account credentials are provided.

Behavior:
- `load_user_state(user_id)`/`save_user_state(user_id, state, memory)` are
  exported and use the configured backend. By default local-only.
"""
from __future__ import annotations

import os
import json
import sqlite3
from typing import Optional, Tuple
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.state import MaternalBrainState
from app.core.memory import Memory

LOGGER = logging.getLogger(__name__)


def _user_dir(user_id: str, base: str = "data/user_states") -> str:
    return os.path.join(base, user_id)


def _ensure_user_dir(user_id: str, base: str = "data/user_states") -> str:
    d = _user_dir(user_id, base)
    os.makedirs(d, exist_ok=True)
    return d


def _get_key_path(user_dir: str) -> str:
    return os.path.join(user_dir, ".secret.key")


def _load_or_create_key(user_dir: str) -> bytes:
    key_path = _get_key_path(user_dir)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()

    # Generate a new key and save it with restrictive permissions
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    try:
        os.chmod(key_path, 0o600)
    except Exception:
        # Windows may not support chmod as expected; ignore
        pass
    return key


class LocalEncryptedSQLite:
    """Stores JSON blobs encrypted in a local SQLite DB per user.

    Table: blobs(key TEXT PRIMARY KEY, value BLOB)
    Keys: 'state', 'memory'
    """

    def __init__(self, base: str = "data/user_states"):
        self.base = base

    def _db_path(self, user_id: str) -> str:
        d = _ensure_user_dir(user_id, self.base)
        return os.path.join(d, "storage.db")

    def _ensure_db(self, path: str):
        conn = sqlite3.connect(path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS blobs (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )""")
            conn.commit()
        finally:
            conn.close()

    def save(self, user_id: str, state: MaternalBrainState, memory: Memory) -> None:
        path = self._db_path(user_id)
        self._ensure_db(path)
        user_dir = os.path.dirname(path)
        key = _load_or_create_key(user_dir)
        f = Fernet(key)

        sjson = json.dumps(state.to_dict(), ensure_ascii=False).encode("utf-8")
        mjson = json.dumps(memory.to_dict(), ensure_ascii=False).encode("utf-8")

        s_enc = f.encrypt(sjson)
        m_enc = f.encrypt(mjson)

        conn = sqlite3.connect(path)
        try:
            conn.execute("REPLACE INTO blobs (key, value) VALUES (?, ?)", ("state", s_enc))
            conn.execute("REPLACE INTO blobs (key, value) VALUES (?, ?)", ("memory", m_enc))
            conn.commit()
        finally:
            conn.close()

    def load(self, user_id: str) -> Optional[Tuple[MaternalBrainState, Memory]]:
        path = self._db_path(user_id)
        if not os.path.exists(path):
            return None

        user_dir = os.path.dirname(path)
        key = _load_or_create_key(user_dir)
        f = Fernet(key)

        conn = sqlite3.connect(path)
        try:
            cur = conn.execute("SELECT key, value FROM blobs WHERE key IN ('state','memory')")
            rows = {k: v for k, v in cur.fetchall()}
        finally:
            conn.close()

        if "state" not in rows or "memory" not in rows:
            return None

        try:
            sjson = f.decrypt(rows["state"]).decode("utf-8")
            mjson = f.decrypt(rows["memory"]).decode("utf-8")
        except InvalidToken:
            LOGGER.exception("Failed to decrypt persisted user data; key mismatch")
            return None

        try:
            sdata = json.loads(sjson)
            mdata = json.loads(mjson)
            state = MaternalBrainState.from_dict(sdata)
            memory = Memory.from_dict(mdata)
            return state, memory
        except Exception:
            LOGGER.exception("Failed to parse persisted JSON")
            return None


# Simple orchestration: by default use local encrypted SQLite
DEFAULT_BACKEND = LocalEncryptedSQLite()


def save_user_state(user_id: str, state: MaternalBrainState, memory: Memory) -> None:
    try:
        DEFAULT_BACKEND.save(user_id, state, memory)
    except Exception:
        LOGGER.exception("Local save failed; falling back to plain JSON")
        # Fallback to original JSON files (best-effort)
        d = _ensure_user_dir(user_id)
        state_path = os.path.join(d, "state.json")
        mem_path = os.path.join(d, "memory.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        with open(mem_path, "w", encoding="utf-8") as f:
            json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)


def load_user_state(user_id: str) -> Optional[Tuple[MaternalBrainState, Memory]]:
    try:
        return DEFAULT_BACKEND.load(user_id)
    except Exception:
        LOGGER.exception("Local load failed; trying JSON files")
        d = _user_dir(user_id)
        state_path = os.path.join(d, "state.json")
        mem_path = os.path.join(d, "memory.json")
        if not os.path.exists(state_path) or not os.path.exists(mem_path):
            return None
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                sdata = json.load(f)
            with open(mem_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            state = MaternalBrainState.from_dict(sdata)
            memory = Memory.from_dict(mdata)
            return state, memory
        except Exception:
            LOGGER.exception("Failed to load fallback JSON state")
            return None


######### Mobile backup / restore helpers #########
import base64
import time


def create_backup_package(user_id: str) -> bytes:
    """Create a portable backup package (bytes) containing the encrypted
    blobs stored for a user. The package DOES NOT include the encryption
    key; the receiving device must have the user's key in its secure
    keystore to decrypt.

    Format (JSON bytes):
    {
      "version": 1,
      "user_id": "...",
      "created_at": 167...,
      "blobs": { "state": "BASE64(...)", "memory": "BASE64(...)" }
    }
    """
    # Read raw encrypted blobs from DB if present
    path = DEFAULT_BACKEND._db_path(user_id)
    if not os.path.exists(path):
        raise FileNotFoundError("No local storage found for user")

    conn = sqlite3.connect(path)
    try:
        cur = conn.execute("SELECT key, value FROM blobs WHERE key IN ('state','memory')")
        rows = {k: v for k, v in cur.fetchall()}
    finally:
        conn.close()

    if not rows:
        raise ValueError("No blobs present to back up")

    payload = {
        "version": 1,
        "user_id": user_id,
        "created_at": int(time.time()),
        "blobs": {k: base64.b64encode(v).decode("ascii") for k, v in rows.items()}
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def save_backup_to_path(user_id: str, dest_path: str) -> str:
    """Create backup package and write to `dest_path`. Returns path."""
    data = create_backup_package(user_id)
    d = os.path.dirname(dest_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)
    return dest_path


def load_backup_package(user_id: str, package_bytes: bytes) -> None:
    """Restore encrypted blobs from a backup package into the user's local
    storage. This writes the encrypted blob bytes directly into the DB;
    decryption will only succeed if the device holds the correct key.
    """
    payload = json.loads(package_bytes.decode("utf-8"))
    blobs = payload.get("blobs", {})
    if not blobs:
        raise ValueError("Backup package contains no blobs")

    # Ensure DB
    db_path = DEFAULT_BACKEND._db_path(user_id)
    DEFAULT_BACKEND._ensure_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        for k, b64 in blobs.items():
            raw = base64.b64decode(b64.encode("ascii"))
            conn.execute("REPLACE INTO blobs (key, value) VALUES (?, ?)", (k, raw))
        conn.commit()
    finally:
        conn.close()


def get_backup_bytes_for_mobile(user_id: str) -> bytes:
    """Alias for mobile clients: returns package bytes ready for upload to
    the user's cloud (Drive/OneDrive/iCloud) from the client app.
    """
    return create_backup_package(user_id)


