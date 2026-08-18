# Contributing

1. Fork and branch from `main`.
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -e ".[dev]"`
4. Add tests under `tests/`.
5. Run:
   ```bash
   YODMCP_MEMORY_BACKEND=memory YODMCP_ATTEST_MODE=software PYTHONPATH=src pytest tests/ -v
   PYTHONPATH=src python scripts/verify_e2e.py
   ```
6. Open a PR against `main`.

See `docs/ARCHITECTURE.md`, `AGENTS.md`, and the **Verify** section of `README.md`.
