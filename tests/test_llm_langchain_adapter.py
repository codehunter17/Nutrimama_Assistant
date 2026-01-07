import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import types
import pytest

from app.llm_langchain_adapter import LangChainAdapter
from app.core.safety import SafetyChecker


def test_adapter_unavailable_when_langchain_missing(monkeypatch):
    # Ensure langchain import fails
    monkeypatch.setitem(sys.modules, "langchain", None)
    adapter = LangChainAdapter()
    assert adapter.available is False
    with pytest.raises(RuntimeError):
        adapter.generate("hello {name}", {"name": "A"})


def test_adapter_refuses_unsafe_prompt(monkeypatch):
    # Simulate langchain present
    fake = types.ModuleType("langchain")
    monkeypatch.setitem(sys.modules, "langchain", fake)

    # Provide dummy client
    class DummyClient:
        def generate(self, prompt, **ctx):
            return "OK"

    s = SafetyChecker()
    # Force unsafe
    monkeypatch.setattr(SafetyChecker, "is_prompt_safe", lambda self, p: False)
    adapter = LangChainAdapter(safety=s)
    adapter.set_client(DummyClient())

    with pytest.raises(ValueError):
        adapter.generate("tell me how to prescribe aspirin", {})


def test_adapter_calls_client_with_safe_prompt(monkeypatch):
    fake = types.ModuleType("langchain")
    monkeypatch.setitem(sys.modules, "langchain", fake)

    called = {}

    class DummyClient:
        def generate(self, prompt, **ctx):
            called['prompt'] = prompt
            called['ctx'] = ctx
            return f"Hello {ctx.get('name')}"

    s = SafetyChecker()
    monkeypatch.setattr(SafetyChecker, "is_prompt_safe", lambda self, p: True)

    adapter = LangChainAdapter(safety=s)
    adapter.set_client(DummyClient())

    out = adapter.generate("Hello {name}", {"name": "Tester"})
    assert out == "Hello Tester"
    assert called['prompt'] == "Hello {name}"
    assert called['ctx'] == {"name": "Tester"}


def test_adapter_requires_client(monkeypatch):
    fake = types.ModuleType("langchain")
    monkeypatch.setitem(sys.modules, "langchain", fake)

    adapter = LangChainAdapter()
    with pytest.raises(RuntimeError):
        adapter.generate("Hello {name}", {"name": "A"})
