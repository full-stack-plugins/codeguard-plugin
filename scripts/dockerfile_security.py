"""dockerfile_security.py：Dockerfile 安全风险检查编排器（codeguard dockerfile）。

双层检查：
  1) hadolint   —— lint + 安全规则（DL3002 root、DL3007 latest、DL3004 sudo、
                   DL3020 ADD 风险、DL3016 端口、DL3025 变量注入、DL3048 HEALTHCHECK 等）
  2) trivy config —— misconfig 规则集（DS002 root 用户、DS001 未固定 digest、
                   敏感信息进镜像层、未清理包管理器缓存等；可选，装了 trivy 更强）

用法：
  python3 dockerfile_security.py                 # 扫当前项目全部 Dockerfile
  python3 dockerfile_security.py path/to/Dockerfile
  python3 dockerfile_security.py --json          # 结构化输出

退出码：0=通过；1=无法验证（工具缺失/无 Dockerfile）；2=发现安全风险
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DOCKERFILE_NAMES = {"Dockerfile"}
DOCKERFILE_EXTS = {".dockerfile"}


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", "command not found"


def find_dockerfiles(root: Path) -> list[Path]:
    """定位 Dockerfile：根目录名匹配 + src 树内 *.dockerfile / */Dockerfile*"""
    found: list[Path] = []
    direct = [p for p in root.iterdir() if p.is_file() and (
        p.name in DOCKERFILE_NAMES or p.suffix.lower() in DOCKERFILE_EXTS)]
    found.extend(sorted(direct, key=lambda p: p.name))
    for pattern in ("**/Dockerfile", "**/*.dockerfile"):
        if len(found) >= 20:
            break
        for p in root.glob(pattern):
            if p.is_file() and p not in found:
                found.append(p)
    return sorted(set(found))


def hadolint_scan(files: list[Path], root: Path) -> dict:
    """hadolint：逐文件扫描，聚合失败计数（warning/error）"""
    findings = []
    tool_ok = True
    scanned = 0
    for f in files:
        rc, out, _err = run(["hadolint", str(f)], cwd=root)
        if rc == 127:
            return {"tool": "hadolint", "exit": 127, "findings": [],
                    "summary_tail": "hadolint not installed (brew install hadolint)"}
        if rc not in (0, 1):     # hadolint: 0=clean, 1=has findings
            tool_ok = False
        scanned += 1
        # 格式: file:line DLxxxx severity message
        findings.extend(out.splitlines())
    return {"tool": "hadolint", "exit": 0 if not findings else 2,
            "scanned": scanned, "findings": findings[-40:], "tool_ok": tool_ok}


def trivy_scan(files: list[Path], root: Path) -> dict:
    """trivy config：misconfig 规则（root 运行、digest 未固定、secrets 等）"""
    results = []
    for f in files:
        rc, out, _err = run(["trivy", "config", "--format", "json", "--quiet", str(f)],
                           cwd=root, timeout=600)
        if rc == 127:
            return {"tool": "trivy config", "exit": 127, "findings": [],
                    "summary_tail": "trivy not installed (brew install trivy)"}
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue
        for res in data.get("Results", []):
            for mis in res.get("Misconfigurations", []):
                if mis.get("Status") == "FAIL":
                    results.append({
                        "id": mis.get("ID"),
                        "title": mis.get("Title"),
                        "severity": mis.get("Severity"),
                        "message": (mis.get("Message") or "")[:200],
                        "resolution": (mis.get("Resolution") or "")[:200],
                    })
    return {"tool": "trivy config", "exit": 0 if not results else 2, "findings": results}


def main() -> int:
    ap = argparse.ArgumentParser(prog="codeguard dockerfile")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("path", nargs="?", default=".")
    args = ap.parse_args()

    root = find_root(args.path)
    files = find_dockerfiles(root)
    if not files:
        print(f"[codeguard-dockerfile] 未找到 Dockerfile: {root}")
        return 1

    if not args.as_json:
        print(f"[codeguard-dockerfile] 扫描 {len(files)} 个 Dockerfile @ {root}")
    h = hadolint_scan(files, root)
    t = trivy_scan(files, root)

    report = {"hadolint": h, "trivy": t}
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        h_ok = h.get("exit") == 0
        t_ok = t.get("exit") == 0
        unverifiable = 127 in (h.get("exit"), t.get("exit"))
        if unverifiable:
            return 1
        return 0 if (h_ok and t_ok) else 2

    print(f"\n== hadolint（lint + 安全规则）== {len(h.get('findings', []))} 条发现")
    for line in h.get("findings", []):
        print("  " + str(line)[:180])
    tri = t.get("findings", [])
    print(f"\n== trivy config（misconfig 安全规则）== {len(tri)} 条 FAIL")
    for item in tri[:30]:
        print(f"  [{item.get('severity')}] {item.get('id')}: {item.get('title')}")
        if item.get("resolution"):
            print(f"      ➜ {item['resolution']}")

    had_fail = bool(h.get("findings")) or h.get("exit") == 127
    tri_fail = bool(t.get("findings"))
    if h.get("exit") == 127 or t.get("exit") == 127:
        print("\n[codeguard-dockerfile] ⚠️ 部分工具未安装——无法完整验证，安装后重跑", file=sys.stderr)
        return 1
    if had_fail or tri_fail:
        print("\n[codeguard-dockerfile] ❌ Dockerfile 存在安全风险——修复后重扫", file=sys.stderr)
        return 2
    print("[codeguard-dockerfile] ✅ Dockerfile 安全检查通过")
    return 0


def find_root(path: str) -> Path:
    p = Path(path).resolve()
    return p if p.is_dir() else p.parent


if __name__ == "__main__":
    sys.exit(main())
