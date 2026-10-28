"""Platform-neutral launcher; all checking stays in the existing command modules."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = {
    "java-plan": "java_project.py",
    "check": "run_check.py",
    "fix": "fix.py",
    "cve": "cve_check.py",
    "dockerfile": "dockerfile_security.py",
    "detect": "detect_lang.py",
    "engine": "engine_report.py",
    "explain": "explain_cli.py",
}
LIFECYCLE = {
    "init", "version", "discover", "doctor", "status", "report", "hooks",
    "impact", "install", "uninstall", "upgrade", "completion",
}


def main(arguments):
    command = arguments[0] if arguments else "check"
    args = arguments[1:] if arguments else []
    if command in LIFECYCLE:
        script = "guard_cli.py"
        args = [command, *args]
    elif command in SCRIPTS:
        script = SCRIPTS[command]
        if command == "detect":
            args = [args[0] if args and args[0] else "."]
    else:
        print(f"codeguard: 未知子命令 '{command}'", file=sys.stderr)
        print("可用: check | fix | cve | dockerfile | detect | java-plan | engine | init", file=sys.stderr)
        return 1
    entry = ROOT / script
    sys.argv = [str(entry), *args]
    runpy.run_path(str(entry), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
