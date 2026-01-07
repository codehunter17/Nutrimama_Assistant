# WIP — Resume guide (Checkpoint: 2026-01-08)

## Checkpoint
- Tag: `checkpoint-2026-01-08`
- Commit: `chore: checkpoint — save work to resume tomorrow`

## Current status
- All unit tests passing locally: **29 passed, 1 skipped, 1 warning**.
- Responder tests and LLM-related tests are passing.
- LLM polish validation relaxed and documented in `docs/llm.md`.
- Changes committed and pushed to `main` and tagged as above.

## Important notes
- Local user state and per-user keys are in `data/` (this directory is ignored by git; do NOT commit `.secret.key`).
- If testing restore flows, ensure the correct `.secret.key` is present on the device before restoring backups.

## Files worth reviewing first
- `app/interface/responder.py` (family-tone responder, LLM polishing)
- `docs/llm.md` (updated guidance about LLM validation)
- `app/llm_client.py`, `app/llm_langchain_adapter.py` (optional LangChain) 
- `app/storage.py`, `app/drive_backup.py`, `app/onedrive_backup.py` (backup/restore helpers)
- `tests/test_responder_style.py`, `tests/test_responder_llm.py` (responder tests)

## Next steps (priority order)
1. Harden Responder tests: add language-aware assertions and reduce brittle exact-string tests. ✅
2. Add an end-to-end smoke test that ensures `SafetyChecker` blocks medical advice and that no medical instructions are returned. ✅
3. Add an optional manual integration test harness for LangChain/LLM (opt-in; requires secrets).
4. Review and expand family phrases for other languages if needed (i18n checklist).
5. Open a PR with the Responder polish fix and doc update (if you want a review). 

## Quick start to resume
1. Pull: `git pull`
2. Activate venv: `.venv\Scripts\Activate.ps1` or `.venv\Scripts\activate`
3. Run tests: `python -m pytest -q`
4. Start at: `app/interface/responder.py` (tests live in `tests/`)

---

If you want, assign one of the next-step items to me and I will start on it immediately when you say so.