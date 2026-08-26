# YodMCP Tool Definition Quality (TDQS) audit

Target: raise Glama [Tool Scores](https://glama.ai/mcp/servers/ANAMIZED/YodMCP/score)
from C (mean 2.4 / min 1.6) toward tier **A (≥ 3.5)**. A literal 5.0 on every
dimension of every tool is not how TDQS is calibrated — Parameter Semantics
baselines at 3 when schema coverage is already high, and Behavioral Transparency
does not reward restating annotations.

Formula used by Glama:

```
descriptionQualityScore = round1(0.6 × mean(TDQS) + 0.4 × min(TDQS))
overall = 0.7 × TDQS + 0.3 × Server Coherence
```

## What shipped (HEAD)

| Lever | Status |
|-------|--------|
| Purpose = verb + resource + sibling boundary | Yes, every core tool |
| Usage guidelines = when / when-not / named alternative | Yes |
| MCP annotations on all 21 tools | Yes (`src/yodmcp/tools/hints.py`) |
| Input schema `description` on every property | Yes (live dump: 100%) |
| Output schema present | Yes (SDK `structured_output` object schema) |
| Completeness CRUD gaps called out by Glama | Closed: memory/plan delete, tasks list/update |
| Existing tool names preserved | Yes |

Live `list_tools()` on this tree: **21 tools**, all annotated.

## Coherence (30% of overall)

Glama's last scan (pre-CRUD, 17 tools):

| Dimension | Was | Expected after this tree |
|-----------|-----|--------------------------|
| Disambiguation | 4/5 | 4–5 (descriptions now name the confused sibling) |
| Naming consistency | 3/5 | 3 (names frozen: `echo`, `discover_capabilities`) |
| Tool count | 4/5 | 3–4 (21 is still justified for an Agent OS) |
| Completeness | 3/5 | 4–5 (delete/list/update added) |

`tasks_cancel` is the task-lifecycle delete. There is no separate `tasks_delete`
so we do not grow the surface again.

## How Glama will see this

1. CI on `main` is green (run 75+).
2. Create a **GitHub Release** from `main` (`v0.5.0`). Glama indexes releases,
   not arbitrary commits. The connected GitHub tools here can push files but
   cannot mint releases — run locally:
   ```bash
   git tag -a v0.5.0 -m "TDQS + CRUD completeness"
   git push origin v0.5.0
   gh release create v0.5.0 --title "v0.5.0" --generate-notes
   ```
3. In the Glama server admin UI, **Sync Server**.
4. Seed usage with **Try in Browser** (the score page flagged 0 usage / 30 days).

## Local verification

```bash
PYTHONPATH=src pytest tests/test_tdqs_tools.py -v
PYTHONPATH=src python scripts/verify_e2e.py
```
