#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime


def _send(proc, payload):
    proc.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode())
    proc.stdin.flush()


def _read_until_id(proc, req_id):
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("codex app-server closed stdout")
        msg = json.loads(line.decode("utf-8", errors="ignore").strip())
        if msg.get("id") == req_id:
            if "error" in msg:
                raise RuntimeError(msg["error"].get("message", "unknown rpc error"))
            return msg.get("result", {})


def _fmt_reset(epoch):
    if epoch is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(epoch))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def main():
    codex_bin = shutil.which("codex")
    if not codex_bin:
        print(json.dumps({"ok": False, "error": "codex not found in PATH"}, ensure_ascii=False))
        return 2

    env = os.environ.copy()
    proc = subprocess.Popen(
        [codex_bin, "-s", "read-only", "-a", "untrusted", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        _send(proc, {"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codex-usage-lite", "version": "1.0.0"}}})
        _ = _read_until_id(proc, 1)
        _send(proc, {"method": "initialized", "params": {}})

        _send(proc, {"id": 2, "method": "account/rateLimits/read", "params": {}})
        result = _read_until_id(proc, 2)
        rl = (result or {}).get("rateLimits", {})

        primary = rl.get("primary") or {}
        secondary = rl.get("secondary") or {}
        credits = rl.get("credits") or {}

        out = {
            "ok": True,
            "five_hour": {
                "used_percent": primary.get("usedPercent"),
                "remaining_percent": (100 - primary.get("usedPercent")) if isinstance(primary.get("usedPercent"), (int, float)) else None,
                "resets_at": _fmt_reset(primary.get("resetsAt")),
            },
            "weekly": {
                "used_percent": secondary.get("usedPercent"),
                "remaining_percent": (100 - secondary.get("usedPercent")) if isinstance(secondary.get("usedPercent"), (int, float)) else None,
                "resets_at": _fmt_reset(secondary.get("resetsAt")),
            },
            "credits": {
                "has_credits": credits.get("hasCredits"),
                "unlimited": credits.get("unlimited"),
                "balance": credits.get("balance"),
            } if credits else None,
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
