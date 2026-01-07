"""LangChain adapter (optional).

Goals:
- Provide a minimal wrapper that is *used only for phrasing*.
- Enforce SafetyChecker.is_prompt_safe() before any generation.
- Be optional (no hard dependency on `langchain`).
- Allow injection of a lightweight client (for tests or concrete LLMs).

Usage:
    from app.llm_langchain_adapter import LangChainAdapter
    adapter = LangChainAdapter()
    if adapter.available:
        adapter.set_client(my_client)
        resp = adapter.generate(prompt_template, context)

The adapter never performs reasoning or safety checks itself beyond prompt safety.
"""
from typing import Any, Dict, Optional

from app.core.safety import SafetyChecker


class LangChainAdapter:
    def __init__(self, safety: Optional[SafetyChecker] = None):
        self.safety = safety or SafetyChecker()
        self._client: Optional[Any] = None
        # Detect presence of langchain but do not import heavy pieces eagerly
        try:
            import importlib

            importlib.import_module("langchain")
            self._langchain_available = True
        except Exception:
            self._langchain_available = False

    @property
    def available(self) -> bool:
        """Whether langchain package is available in the environment."""
        return self._langchain_available

    def set_client(self, client: Any) -> None:
        """Set a concrete client instance used to perform generation.

        The client must expose either `generate(prompt, **context)` or
        `run(**context)` / `generate(**context)` style method. Adapter
        intentionally does not create LLM instances itself to keep
        dependency injection simple and testable.
        """
        self._client = client

    def generate(self, prompt_template: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Generate text using the configured langchain client.

        Args:
            prompt_template: The prompt template string (formatted by client)
            context: dict with variables used to fill the prompt
        Returns:
            Generated text
        Raises:
            ValueError if prompt is unsafe
            RuntimeError if the adapter is not available or client not set
        """
        # Safety first: prompts must be conservative
        if not self.safety.is_prompt_safe(prompt_template):
            raise ValueError("Prompt rejected by SafetyChecker: unsafe content")

        if not self.available:
            raise RuntimeError("LangChain not available in environment")

        if self._client is None:
            raise RuntimeError("LangChain client not configured; call set_client()")

        # Support a tiny set of client interfaces to stay implementation-agnostic
        # Prefer `generate(prompt, **context)` then `run(**context)` then `generate(**context)`
        args = (prompt_template,)
        kwargs = kwargs or {}
        ctx = context or {}

        # If client offers `generate(prompt, **ctx)`
        if hasattr(self._client, "generate"):
            try:
                return self._client.generate(prompt_template, **ctx)
            except TypeError:
                # fallback to generate(**ctx)
                return self._client.generate(**ctx)

        if hasattr(self._client, "run"):
            return self._client.run(**ctx)

        raise RuntimeError("Configured LangChain client does not support expected interfaces")
