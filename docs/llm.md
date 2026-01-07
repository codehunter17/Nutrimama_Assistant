# LLM integration (Responder)

This project uses LLMs only for phrasing and tone — not for decisions.

- `app/llm_client.py` provides a pluggable client. By default it uses `LocalMockClient`.
- If `OPENAI_API_KEY` is set and `openai` is installed, `OpenAIClient` will be used.
- The Responder (`app/interface/responder.py`) calls the LLM only after a safety check via `SafetyChecker`.
- Responder accepts LLM-polished output if it passes a basic non-echo check (it must not contain prompt-template text). Short one-line polishes are allowed — the responder no longer requires a blank-line structure.
- All LLM calls are stochastic; the system uses deterministic templates as a fallback to ensure consistent behavior and testability.

Environment variables:

- `OPENAI_API_KEY` — optional, set to use OpenAI as provider.
- `OPENAI_MODEL`, `OPENAI_TEMP` — optional model and temperature overrides.

Security and privacy:

- LLMs only receive sanitized prompts that avoid PII and any request that could cause medical advice to be given.
- If a prompt fails safety checks, the LLM will not be called and the system will use deterministic templates.

Testing:

- LLM client is mocked in tests (see `tests/test_responder_llm.py`).

### LangChain adapter (optional)

A minimal LangChain adapter (`app/llm_langchain_adapter.py`) is provided as an optional integration for teams that prefer LangChain tooling for prompt templating, caching, or instrumentation. Important constraints:

- **LangChain must never be used for reasoning or safety decisions.** Use it only in the Responder layer for phrasing.
- The adapter enforces `SafetyChecker.is_prompt_safe()` before generating text.
- The adapter is optional: it detects whether `langchain` is present and requires a client to be injected via `set_client()`.

Example usage:

```py
from app.llm_langchain_adapter import LangChainAdapter
adapter = LangChainAdapter()
if adapter.available:
    adapter.set_client(my_langchain_client)
    text = adapter.generate("Hello {name}", {"name": "Ada"})
else:
    # fall back to deterministic template in responder
    text = "Hello Ada"
```

If you decide to use LangChain, install it explicitly in your environment. Do NOT add it to core runtime dependencies unless you plan to use it across the system; keep it opt-in and well-contained.

### Operator Guide: wiring LangChain + OpenAI (example)

If you intend to use LangChain for templating and observability in production, follow these steps (example using OpenAI):

1. Install packages into the runtime environment (opt-in):

```bash
pip install langchain openai
```

2. Provide the OpenAI key as an environment variable (or other secret store):

- `OPENAI_API_KEY` — set in the environment or secret manager used by your deployment platform (do NOT commit this to source).

3. Create and inject a LangChain client into the adapter during application initialization (example):

```py
# bootstrap.py (example)
from langchain.llms import OpenAI
from app.llm_langchain_adapter import LangChainAdapter

adapter = LangChainAdapter()
if adapter.available:
    llm_client = OpenAI(temperature=0)
    adapter.set_client(llm_client)

# Pass `adapter` to your Responder or make it available via DI
```

4. Important operational notes:
- Keep prompt templates conservative and run all prompts through `SafetyChecker.is_prompt_safe()` (the adapter enforces this by default).
- Instrument and log LLM usage (tokens, latency, prompt hashes) for cost/audit tracking.
- Perform manual integration tests using the provided manual CI job (see below).

### CI: Opt-in LangChain integration job

A manual GitHub Actions job is available to run LangChain integration tests (`.github/workflows/langchain-integration.yml`). This job only runs when manually dispatched with `run: yes` and requires the `OPENAI_API_KEY` to be added to the repository secrets. This keeps LangChain integration testing opt-in and prevents accidental use of secrets in ordinary CI runs.

*** End Patch