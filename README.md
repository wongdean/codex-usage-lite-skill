# codex-usage-lite

极简：本地查询 Codex 额度（默认只看 **5小时** 和 **周**）。

## 运行

```bash
python3 scripts/fetch_codex_usage.py
```

## 返回字段

- `five_hour.used_percent` / `remaining_percent` / `resets_at`
- `weekly.used_percent` / `remaining_percent` / `resets_at`

> 默认不展示月度 credits（除非你明确要看）。
