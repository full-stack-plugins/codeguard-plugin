"""Install the CodeGuard launcher into a user bin directory."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bin" / "codeguard"
DEFAULT_BIN = Path.home() / ".local" / "bin"


def target(argv):
    if "--bin-dir" in argv:
        return Path(argv[argv.index("--bin-dir") + 1]).expanduser().resolve() / "codeguard"
    return DEFAULT_BIN / "codeguard"


def payload(command, decision, **extra):
    code = {"allow": 0, "deny": 1, "error": 2, "unverified": 3}.get(decision, 4)
    return {"schemaVersion": "partme.guard/v1", "tool": "codeguard", "command": f"codeguard.{command}",
            "decision": decision, "exitCode": code, "findings": [], "evidence": {}, **extra}


def main(argv):
    command = argv[0] if argv else "install"
    path = target(argv)
    if command == "completion":
        shell = argv[1] if len(argv) > 1 else "bash"
        if shell not in ("bash", "zsh", "fish"):
            print("usage: codeguard completion bash|zsh|fish", file=sys.stderr)
            return 2
        commands = "version discover doctor status report init impact check fix cve dockerfile hooks engine completion"
        if shell == "fish":
            print("complete -c codeguard -f -a '" + commands + "'")
        else:
            print("# codeguard " + shell + " completion")
            print("complete -W '" + commands + "' codeguard" if shell == "bash"
                  else "compdef '_arguments " + repr(commands) + "' codeguard")
        return 0
    if command not in ("install", "uninstall", "upgrade"):
        print("usage: codeguard install|uninstall|upgrade [--bin-dir DIR] [--dry-run]", file=sys.stderr)
        return 2
    if command == "uninstall":
        if not path.is_symlink() or path.resolve() != SOURCE.resolve():
            print(json.dumps(payload("uninstall", "deny", error="not_managed", path=str(path)), ensure_ascii=False))
            return 1
        if "--dry-run" in argv:
            print(json.dumps(payload("uninstall", "allow", dryRun=True, path=str(path)), ensure_ascii=False))
            return 0
        path.unlink()
        print(json.dumps(payload("uninstall", "allow", removed=str(path)), ensure_ascii=False))
        return 0
    if path.exists() and not path.is_symlink():
        print(json.dumps(payload(command, "deny", error="target_exists", path=str(path)), ensure_ascii=False))
        return 1
    if path.is_symlink() and path.resolve() != SOURCE.resolve():
        print(json.dumps(payload(command, "deny", error="target_is_other_symlink", path=str(path)), ensure_ascii=False))
        return 1
    if "--dry-run" in argv:
        print(json.dumps(payload(command, "allow", dryRun=True, source=str(SOURCE), target=str(path)), ensure_ascii=False))
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()
    os.symlink(SOURCE, path)
    print(json.dumps(payload(command, "allow", installed=True, source=str(SOURCE), target=str(path)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
