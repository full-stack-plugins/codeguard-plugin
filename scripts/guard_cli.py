"""CodeGuard lifecycle and project-fact commands."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

def envelope(command, decision, findings=None, **extra):
    return {"schemaVersion":"partme.guard/v1","tool":"codeguard","command":command,
            "decision":decision,"exitCode":{"allow":0,"deny":1,"error":2,"unverified":3,"internal":4}[decision],
            "findings":findings or [], "evidence":{}, **extra}

def load_manifest():
    return json.loads((ROOT/"plugin.json").read_text())

def project_root(path="."):
    from detect_lang import find_project_root
    return Path(find_project_root(path) or path).resolve()

def languages(root):
    from detect_lang import detect_languages
    return detect_languages(root)

def config_path(root):
    return root/"codeguard.json"

def hook_path(root):
    return root/".git"/"hooks"/"pre-commit"

def last_log(root):
    return root/"out"/".codeguard-last.log"

def cmd_version(args):
    m=load_manifest()
    result=envelope("codeguard.version","allow",version=m["version"],protocol="partme.guard/v1")
    print(json.dumps(result,ensure_ascii=False,indent=2) if "--json" in args else f"codeguard {m['version']} (partme.guard/v1)")
    return 0

def cmd_discover(args):
    root=project_root(args[-1] if args and not args[-1].startswith("-") else ".")
    data=languages(root)
    result=envelope("codeguard.discover","allow",project={"root":str(root)},languages=data)
    print(json.dumps(result,ensure_ascii=False,indent=2) if "--json" in args else json.dumps(data,ensure_ascii=False,indent=2))
    return 0

def cmd_doctor(args):
    root=project_root(args[-1] if args and not args[-1].startswith("-") else ".")
    findings=[]
    checks={}
    checks["python"]=sys.version.split()[0]
    checks["git"]=bool(shutil.which("git"))
    if not checks["git"]: findings.append({"code":"GIT_MISSING","severity":"warning"})
    checks["config"]=config_path(root).is_file()
    checks["hooks"]=hook_path(root).is_file()
    checks["lastLog"]=last_log(root).is_file()
    decision="allow" if not [f for f in findings if f["severity"]=="blocker"] else "deny"
    result=envelope("codeguard.doctor",decision,findings=findings,project={"root":str(root)},checks=checks)
    print(json.dumps(result,ensure_ascii=False,indent=2) if "--json" in args else json.dumps(checks,ensure_ascii=False,indent=2))
    return result["exitCode"]


def cmd_status(args):
    root=project_root(args[-1] if args and not args[-1].startswith("-") else ".")
    result=envelope("codeguard.status","allow",project={"root":str(root)},status={
        "languages":languages(root),"config":str(config_path(root)),"configExists":config_path(root).is_file(),
        "hooks":str(hook_path(root)),"hooksInstalled":hook_path(root).is_file(),
        "lastLog":str(last_log(root)),"lastLogExists":last_log(root).is_file()})
    print(json.dumps(result,ensure_ascii=False,indent=2) if "--json" in args else json.dumps(result["status"],ensure_ascii=False,indent=2))
    return 0

def cmd_report(args):
    root=project_root(args[-1] if args and not args[-1].startswith("-") else ".")
    log=last_log(root)
    text=log.read_text(errors="replace")[-4000:] if log.is_file() else ""
    result=envelope("codeguard.report","allow" if log.is_file() else "unverified",project={"root":str(root)},report={"log":str(log),"exists":log.is_file(),"tail":text})
    print(json.dumps(result,ensure_ascii=False,indent=2) if "--json" in args else text or "no codeguard report found")
    return result["exitCode"]

def cmd_init(args):
    root=project_root(args[-1] if args and not args[-1].startswith("-") else ".")
    dry="--dry-run" in args
    target=config_path(root)
    content={"version":1,"extensions":{},"exclude":[]}
    if target.exists():
        print(json.dumps({"decision":"allow","unchanged":True,"path":str(target)},ensure_ascii=False))
        return 0
    if dry:
        print(json.dumps({"decision":"allow","dryRun":True,"path":str(target),"content":content},ensure_ascii=False))
        return 0
    target.write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"decision":"allow","created":str(target)},ensure_ascii=False))
    return 0

COMMANDS={"version":cmd_version,"discover":cmd_discover,"doctor":cmd_doctor,"status":cmd_status,"report":cmd_report,"init":cmd_init}

def main(argv):
    if argv and argv[0] == "hooks":
        from hooks_cli import main as hooks_main
        return hooks_main(argv[1:])
    if not argv or argv[0] not in COMMANDS:
        print("usage: codeguard version|discover|doctor|status|report|init [--json] [path]",file=sys.stderr);return 2
    return COMMANDS[argv[0]](argv[1:])

if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
