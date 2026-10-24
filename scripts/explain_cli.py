"""Explain a CodeGuard language rule or the last check log."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def result(decision, **extra):
    code = {"allow": 0, "deny": 1, "error": 2, "unverified": 3}.get(decision, 4)
    return {"schemaVersion": "partme.guard/v1", "tool": "codeguard", "command": "codeguard.explain",
            "decision": decision, "exitCode": code, "findings": [], "evidence": {}, **extra}


def main(argv):
    languages = json.loads((ROOT / "scripts" / "languages.json").read_text())["languages"]
    if "--last" in argv:
        log = Path.cwd() / "out" / ".codeguard-last.log"
        text = log.read_text(errors="replace")[-4000:] if log.is_file() else ""
        payload = result("allow" if text else "unverified", log=str(log), tail=text)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload["exitCode"]
    subject = next((a for a in argv if not a.startswith("-")), "")
    if not subject:
        payload = result("allow", subjects=[{"id": x["id"], "name": x["name"], "status": x["status"]} for x in languages])
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    item = next((x for x in languages if x["id"] == subject or x["name"].lower() == subject.lower()), None)
    if item is None:
        payload = result("unverified", findings=[{"code": "UNKNOWN_SUBJECT", "severity": "warning"}], subject=subject)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 3
    payload = result("allow", subject=item["id"], language={
        "name": item["name"], "status": item["status"], "lint": item.get("lint"),
        "format": item.get("format"), "installHint": item.get("install_hint"),
        "markers": item.get("markers", []), "configFiles": item.get("linter_config_files", [])})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
