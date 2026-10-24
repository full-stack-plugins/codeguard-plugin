"""Install and inspect the repository pre-commit hook."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "# codeguard-managed"


def git_dir(root: Path):
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"], capture_output=True, text=True, check=False)
    if out.returncode:
        return None
    return (root / out.stdout.strip()).resolve()


def hook_path(root: Path):
    directory = git_dir(root)
    return None if directory is None else directory / "hooks" / "pre-commit"


def status(root: Path):
    path = hook_path(root)
    if path is None:
        return {"git": False, "installed": False, "managed": False, "executable": False, "path": None}
    text = path.read_text(errors="replace") if path.is_file() else ""
    return {"git": True, "installed": path.is_file(), "managed": MARKER in text,
            "executable": bool(path.is_file() and path.stat().st_mode & 0o111), "path": str(path)}


def main(argv):
    action = argv[0] if argv else "status"
    root = Path.cwd().resolve()
    if action == "status":
        data = status(root)
        print(json.dumps({"tool": "codeguard", "command": "codeguard.hooks.status", "hooks": data}, ensure_ascii=False, indent=2))
        return 0
    if action != "install":
        print("usage: codeguard hooks install|status [--force]", file=sys.stderr)
        return 2
    path = hook_path(root)
    if path is None:
        print(json.dumps({"decision": "deny", "error": "not_a_git_repository"}, ensure_ascii=False))
        return 1
    if path.exists():
        text = path.read_text(errors="replace")
        if MARKER not in text and "--force" not in argv:
            print(json.dumps({"decision": "deny", "error": "existing_hook_not_managed", "path": str(path)}, ensure_ascii=False))
            return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\n{MARKER}\nexec "{ROOT}/bin/codeguard" check --quiet .\n')
    path.chmod(0o755)
    print(json.dumps({"decision": "allow", "installed": True, "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
