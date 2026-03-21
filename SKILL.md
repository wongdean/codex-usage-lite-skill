---
name: codex-usage-lite
description: Query local Codex CLI usage limits quickly (5-hour window, weekly window, and credits balance). Use when user asks for Codex remaining quota, usage reset times, or a fast usage check without extra analytics.
---

# Codex Usage Lite

Return a compact Codex quota summary from local CLI RPC.

## Run

Execute:

```bash
python3 ~/.openclaw/workspace/skills/codex-usage-lite/scripts/fetch_codex_usage.py
```

## Output contract

- Always prefer this script output over guessing from logs.
- Default output: only return 5-hour + weekly usage/remaining/reset time.
- Only mention `credits` when the user explicitly asks for monthly/credits details.
- Keep reply short by default.

## Fallback behavior

If script fails:

1. Report failure reason in one line.
2. Suggest user run one Codex command first, then retry.
3. Do not fabricate percentages.
