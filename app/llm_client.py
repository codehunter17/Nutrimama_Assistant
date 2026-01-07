"""Pluggable LLM client abstraction.

Provides a simple interface for generating toneful responses. Default behavior
is to use OpenAI when `OPENAI_API_KEY` is present. The implementation uses
lazy imports so the package can run without OpenAI installed (tests mock the
client instead).

Security: This client MUST NOT be used for decision-making. It is only for
human-friendly wording and tone. Safety filters (see `app.core.safety`) must
be applied before and after calling the model.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

LOGGER = logging.getLogger(__name__)


class LLMClient:
    """Abstract LLM client. Instantiate with `LLMClient.from_env()`.

    Methods:
      - generate_response(prompt: str) -> str
    """

    def generate_response(self, prompt: str, max_tokens: int = 150) -> str:
        raise NotImplementedError

    @staticmethod
    def from_env() -> "LLMClient":
        """Factory: selects provider based on environment variables.

        - If OPENAI_API_KEY present, returns `OpenAIClient`.
        - Otherwise returns `LocalMockClient` which echoes prompts (for dev/tests).
        """
        if os.getenv("OPENAI_API_KEY"):
            try:
                return OpenAIClient()
            except Exception:
                LOGGER.exception("Failed to initialize OpenAIClient; falling back to mock")
        return LocalMockClient()


class LocalMockClient(LLMClient):
    """Simple local client used when no remote LLM available. Deterministic
    and fast for tests and offline development.
    """

    def generate_response(self, prompt: str, max_tokens: int = 150) -> str:
        # Very lightweight: return a polite rephrase using simple heuristics.
        # Keep response short and deterministic for tests.
        header = "(Tone) "
        snippet = prompt.strip().split("\n")[0][:200]
        return f"{header}Thanks for sharing — {snippet}"


class OpenAIClient(LLMClient):
    def __init__(self):
        # Lazy import to avoid hard dependency on import time
        import openai

        openai.api_key = os.getenv("OPENAI_API_KEY")
        self._openai = openai

    def generate_response(self, prompt: str, max_tokens: int = 150) -> str:
        try:
            resp = self._openai.Completion.create(
                model=os.getenv("OPENAI_MODEL", "text-davinci-003"),
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=float(os.getenv("OPENAI_TEMP", "0.7")),
            )
            text = resp.choices[0].text.strip()
            return text
        except Exception:
            LOGGER.exception("OpenAI request failed; falling back to safe message")
            return "Thanks — I hear you. I'm here to help."