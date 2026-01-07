import os
import json
import shutil
from pathlib import Path

import pytest

import sys
from pathlib import Path
# Ensure repository root is on sys.path when running tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.storage as storage
from app.core.state import MaternalBrainState
from app.core.memory import Memory


def test_backup_and_restore_cycle(tmp_path):
    # Point backend to temporary base
    base = tmp_path / "user_states"
    storage.DEFAULT_BACKEND.base = str(base)

    # Create initial state and memory
    user_a = "user_a"
    state = MaternalBrainState()
    state.energy_level = 0.77
    state.nutrition["iron"] = 0.42

    mem = Memory(user_a)
    action_id = mem.log_action("suggest_food", "Eat spinach", "initial test", ["iron"])
    mem.record_outcome(action_id, "positive", "Felt better")

    # Save to local encrypted backend
    storage.save_user_state(user_a, state, mem)

    # Create backup package
    pkg = storage.create_backup_package(user_a)
    assert isinstance(pkg, (bytes, bytearray))

    # Prepare a new user (user_b) and copy key so decryption works
    user_b = "user_b"
    user_a_dir = base / user_a
    user_b_dir = base / user_b
    os.makedirs(user_b_dir, exist_ok=True)

    # Copy secret key to new user
    key_src = user_a_dir / ".secret.key"
    key_dst = user_b_dir / ".secret.key"
    assert key_src.exists()
    shutil.copy(key_src, key_dst)

    # Load backup package into user_b
    storage.load_backup_package(user_b, pkg)

    # Now load from storage and verify
    loaded = storage.load_user_state(user_b)
    assert loaded is not None
    lstate, lmem = loaded

    # Compare main numeric fields
    assert abs(lstate.energy_level - state.energy_level) < 1e-6
    assert abs(lstate.nutrition["iron"] - state.nutrition["iron"]) < 1e-6

    # Compare memory actions
    assert len(lmem.actions) == len(mem.actions)
    assert lmem.actions[0].action_text == mem.actions[0].action_text


def test_save_backup_to_path_and_load(tmp_path):
    storage.DEFAULT_BACKEND.base = str(tmp_path / "user_states2")
    user = "user_c"
    state = MaternalBrainState()
    mem = Memory(user)
    storage.save_user_state(user, state, mem)

    out = tmp_path / "backup.json"
    path = storage.save_backup_to_path(user, str(out))
    assert os.path.exists(path)
    data = out.read_bytes()
    assert b"blobs" in data
