#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


COMMON_PATH_DIRS = (
    Path.home() / ".npm-global" / "bin",
    Path.home() / ".local" / "bin",
    Path.home() / "bin",
)


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


def _npm_prefix_bin():
    npm_bin = shutil.which("npm")
    if not npm_bin:
        return None
    try:
        result = subprocess.run(
            [npm_bin, "config", "get", "prefix"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    prefix = (result.stdout or "").strip()
    if not prefix or prefix == "undefined":
        return None
    return Path(prefix).expanduser() / "bin"


def _resolve_codex_bin():
    env_bin = os.environ.get("CODEX_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin

    direct = shutil.which("codex")
    if direct:
        return direct

    candidates = []
    seen = set()

    def add(candidate):
        path = Path(candidate).expanduser()
        if path in seen:
            return
        seen.add(path)
        candidates.append(path)

    for directory in COMMON_PATH_DIRS:
        add(directory / "codex")

    npm_prefix_bin = _npm_prefix_bin()
    if npm_prefix_bin is not None:
        add(npm_prefix_bin / "codex")

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def _build_child_env(codex_bin):
    env = os.environ.copy()
    path_entries = []
    codex_dir = str(Path(codex_bin).resolve().parent)
    path_entries.append(codex_dir)

    for directory in COMMON_PATH_DIRS:
        path_entries.append(str(directory))

    npm_prefix_bin = _npm_prefix_bin()
    if npm_prefix_bin is not None:
        path_entries.append(str(npm_prefix_bin))

    existing = env.get("PATH", "")
    if existing:
        path_entries.append(existing)

    deduped = []
    seen = set()
    for entry in path_entries:
        if not entry or entry in seen:
            continue
        seen.add(entry)
        deduped.append(entry)

    env["PATH"] = os.pathsep.join(deduped)
    return env


def main():
    codex_bin = _resolve_codex_bin()
    if not codex_bin:
        print(json.dumps({"ok": False, "error": "codex not found in PATH or common npm global bin locations"}, ensure_ascii=False))
        return 2

    env = _build_child_env(codex_bin)
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
