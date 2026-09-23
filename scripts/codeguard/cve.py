"""CVE 应用服务：选择生态、执行审计、显式修复与复扫；不输出宿主协议。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConfigurationError, get_overrides
from .cve_policy import CVSS_BAND_FLOOR, EXIT_USAGE, aggregate_exit
from .cve_scanners import (
    run,
    scan_cargo,
    scan_go,
    scan_maven,
    scan_node,
    scan_pip,
    scan_trivy,
)
from .discovery import detect_languages, find_project_root


def _scan_maven_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_maven(root, CVSS_BAND_FLOOR[severity])


def _scan_node_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    result = scan_node(root, severity, False)
    if allow_fix and result.get("status") == "FAIL":
        argv = ["npm", "audit", "fix"]
        rc, out, err = run(argv, cwd=root, timeout=900)
        after = scan_node(root, severity, False)
        after["before_fix"] = result
        after["fix_execution"] = {"argv": argv, "cwd": str(root), "exit": rc, "stdout": out, "stderr": err}
        return after
    return result


def _scan_pip_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_pip(root, severity)


def _scan_cargo_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_cargo(root, severity)


def _scan_go_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_go(root, severity)


def _scan_trivy_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_trivy(root, severity)


# 唯一生态目录：规范标识、别名、语言、输入与入口一起派生。
ECOSYSTEM_SCANNERS = {
    "maven": {
        "aliases": ("java",),
        "languages": ("java",),
        "markers": ("pom.xml",),
        "scan": _scan_maven_ecosystem,
    },
    "go": {
        "aliases": ("golang", "gomod"),
        "languages": ("go",),
        "markers": ("go.mod", "go.sum"),
        "scan": _scan_go_ecosystem,
    },
    "node": {
        "aliases": (),
        "languages": ("typescript",),
        "markers": ("package.json", "package-lock.json", "npm-shrinkwrap.json"),
        "scan": _scan_node_ecosystem,
    },
    "python": {
        "aliases": (),
        "languages": ("python",),
        "markers": ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile.lock"),
        "scan": _scan_pip_ecosystem,
    },
    "rust": {
        "aliases": (),
        "languages": ("rust",),
        "markers": ("Cargo.lock",),
        "scan": _scan_cargo_ecosystem,
    },
    "universal": {
        "aliases": ("trivy",),
        "languages": (),
        "markers": (),
        "scan": _scan_trivy_ecosystem,
    },
}


def canonical_ecosystem(value: str) -> str | None:
    """生态标识归一化：接受规范标识与其别名；未声明返回 None"""
    key = value.strip().lower()
    if key in ECOSYSTEM_SCANNERS:
        return key
    for canonical, spec in ECOSYSTEM_SCANNERS.items():
        if key in spec["aliases"]:
            return canonical
    return None


def ecosystem_choices() -> str:
    """全部可接受标识（含别名），供错误信息与 --help 共用"""
    parts = []
    for canonical, spec in ECOSYSTEM_SCANNERS.items():
        aliases = spec["aliases"]
        parts.append(f"{canonical}（别名 {'/'.join(aliases)}）" if aliases else canonical)
    return "、".join(parts)


def language_ecosystem_map() -> dict[str, str]:
    """语言 id → 规范生态标识，从权威映射派生"""
    return {lang: canonical
            for canonical, spec in ECOSYSTEM_SCANNERS.items()
            for lang in spec["languages"]}


def precheck(root: Path, eco: str) -> tuple[bool, str]:
    """返回 (可扫描, 说明)。缺少标志文件说明项目不属于该生态（或依赖未锁定），
    运行扫描器只会得到环境错误——归类为「无法验证」而非「有漏洞」。"""
    markers = ECOSYSTEM_SCANNERS.get(eco, {}).get("markers", ())
    if not markers:
        return True, ""
    if any((root / m).exists() for m in markers):
        return True, ""
    return False, f"缺少 {' / '.join(markers)}（可能不是{eco}项目或依赖未锁定）"



@dataclass(frozen=True)
class CveBatch:
    """一次应用调用，CLI 文本和 JSON 使用同一个判定。"""

    root: Path
    ecosystems: tuple[str, ...]
    results: tuple[dict, ...]
    exit_code: int
    error: str = ""


def scan_project(path: str | Path, ecosystem: str | None = None,
                 severity: str = "HIGH", allow_fix: bool = False) -> CveBatch:
    """先验证参数与项目配置，不允许显式生态或 --fix 绕过坏配置。"""
    canonical = canonical_ecosystem(ecosystem) if ecosystem else None
    root = Path(path).resolve()
    if ecosystem and canonical is None:
        return CveBatch(root, (), (), EXIT_USAGE,
                        f"未知生态 {ecosystem!r}；可接受：{ecosystem_choices()}")
    if severity not in CVSS_BAND_FLOOR:
        return CveBatch(root, (), (), EXIT_USAGE, f"未知严重度 {severity!r}")
    root = find_project_root(root) or root
    results = []
    ecosystems = []
    try:
        get_overrides(root)
        if canonical:
            ecosystems = [canonical]
        else:
            languages = detect_languages(root)
            mapping = language_ecosystem_map()
            ecosystems = sorted({mapping[lang] for lang in languages if lang in mapping})
            if languages and not ecosystems:
                ecosystems = ["universal"]
    except ConfigurationError as exc:
        results.append({"ecosystem": canonical or "project", "tool": "configuration", "exit": 1,
                        "status": "UNVERIFIED", "reason": str(exc), "fix_hint": "修复项目配置后重试"})
        return CveBatch(root, tuple(ecosystems), tuple(results), aggregate_exit(results))
    for eco in ecosystems:
        available, reason = precheck(root, eco)
        if not available:
            result = {"ecosystem": eco, "tool": eco, "exit": 127, "status": "UNVERIFIED",
                      "reason": reason, "summary_tail": f"无法验证: {reason}", "fix_hint": "确认项目类型后重试"}
        else:
            result = ECOSYSTEM_SCANNERS[eco]["scan"](root, severity, allow_fix)
            if result.get("status") not in ("PASS", "FAIL", "UNVERIFIED"):
                result = {**result, "status": "UNVERIFIED", "reason": "适配器缺少有效报告判定"}
        results.append(result)
    return CveBatch(root, tuple(ecosystems), tuple(results), aggregate_exit(results))
