import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.interface.responder as responder_mod
from app.interface.responder import Responder


class DummyLLM:
    def __init__(self, text="(LLM) nice message"):
        self.text = text

    def generate_response(self, prompt: str, max_tokens: int = 150):
        return self.text


def test_acknowledge_uses_llm(monkeypatch):
    # Replace LLMClient.from_env to return a dummy LLM
    monkeypatch.setattr(responder_mod.LLMClient, "from_env", staticmethod(lambda: DummyLLM("LLM ack")))
    r = Responder()
    resp = r.acknowledge_user("I'm tired")
    assert resp == "LLM ack"


def test_acknowledge_fallback_on_unsafe(monkeypatch):
    monkeypatch.setattr(responder_mod.LLMClient, "from_env", staticmethod(lambda: DummyLLM("LLM ack")))
    # Make safety return False
    monkeypatch.setattr(responder_mod.SafetyChecker, "is_prompt_safe", lambda self, p: False)
    r = Responder()
    resp = r.acknowledge_user("I'm tired")
    assert "I hear you" in resp or "Thank you" in resp


def test_respond_to_action_uses_llm(monkeypatch):
    monkeypatch.setattr(responder_mod.LLMClient, "from_env", staticmethod(lambda: DummyLLM("LLM action")))
    r = Responder()
    resp = r.respond_to_action("check_in", {"question": "How are you?"}, state=None)
    assert resp == "LLM action"

