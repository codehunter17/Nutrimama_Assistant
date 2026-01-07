import os
import pytest

pytestmark = pytest.mark.integration

RUN_INTEGRATION = os.getenv("RUN_LANGCHAIN_INTEGRATION") == "1"
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


def test_langchain_integration_real_call():
    """Runs a minimal LangChain+OpenAI call only when explicitly enabled.

    Requirements (manually controlled in CI):
      - Set RUN_LANGCHAIN_INTEGRATION=1
      - Set OPENAI_API_KEY secret

    This test is skipped by default to avoid accidental network calls in CI.
    """
    if not RUN_INTEGRATION or not OPENAI_KEY:
        pytest.skip("LangChain integration not enabled or OPENAI_API_KEY missing")

    try:
        from langchain.llms import OpenAI
    except Exception as e:
        pytest.skip(f"LangChain or OpenAI LLM not installed: {e}")

    # Minimal smoke test: create client and make a deterministic call
    llm = OpenAI(temperature=0)
    resp = llm("Say 'hello' and nothing else")
    assert "hello" in resp.lower()
