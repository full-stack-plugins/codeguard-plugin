"""静态架构门禁：内核依赖白名单、顶层脚本角色与第一方 Python 导入环。

只解析 AST，不导入被检查代码。函数内、条件分支中的静态 import 同样检查；
运行时拼接的动态加载不在静态保证范围内，本工具不是安全沙箱或 CodeGraph 替代。
新增内核模块必须在此声明边界，不能依靠目录命名假装分层。
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

# 明确的层依赖；stdlib 也受约束，纯模型不能悄悄导入 subprocess/宿主。
# 顶层 scripts/*.py 的显式角色登记：新脚本必须归类，不许"就是多了一个脚本"。
# entry=命令入口 / compat-shim=旧导入面兼容外观（docstring 必须含 Deprecated）/
# adapter=物化适配层 / support=共享工具层。内核包 codeguard.* 走 CORE_DEPENDENCIES，
# 本表只管包外顶层脚本；两者共同构成可检查的分层边界。
SCRIPT_ROLES = {
    "check_architecture.py": "entry",
    "cve_check.py": "entry",
    "detect_lang.py": "entry",
    "dockerfile_security.py": "entry",
    "fix.py": "entry",
    "gen_language_docs.py": "entry",
    "java_project.py": "entry",
    "run_check.py": "entry",
    "validate_languages_json.py": "entry",
    "verdict.py": "compat-shim",
    "user_config.py": "compat-shim",
    "run_per_language.py": "compat-shim",
    "scope.py": "adapter",
    "git_snapshot.py": "adapter",
    "paths.py": "support",
}

# 适配层白名单：包外实现模块的用途声明（谁在依赖它由 CORE_DEPENDENCIES 约束）。
ADAPTER_LAYERS = {
    "scope.py": "linter 命令作用域物化 + git 改动集（delta 门禁共享层）",
    "git_snapshot.py": "只读 index/HEAD 物化一次性检查目录",
}

CORE_DEPENDENCIES = {
    "codeguard.cve_policy": {"__future__", "dataclasses"},
    "codeguard.cve_reports": {"__future__", "json", "math", "codeguard.cve_policy"},
    "codeguard.cve_scanners": {"__future__", "tempfile", "pathlib", "codeguard.cve_policy",
                               "codeguard.cve_reports", "codeguard.execution"},
    "codeguard.cve": {"__future__", "dataclasses", "pathlib", "codeguard.config", "codeguard.discovery",
                      "codeguard.cve_policy", "codeguard.cve_scanners"},
    "codeguard.dockerfile_reports": {"__future__", "dataclasses", "json"},
    "codeguard.dockerfile": {"__future__", "pathlib", "codeguard.dockerfile_reports",
                             "codeguard.execution"},
    "codeguard": {"__future__"},
    "codeguard.models": {"__future__", "dataclasses", "pathlib", "typing"},
    "codeguard.verdict": {"__future__", "re", "posixpath", "collections", "collections.abc",
                          "pathlib", "codeguard.models"},
    "codeguard.execution": {"__future__", "os", "signal", "subprocess", "tempfile", "contextlib", "threading", "time",
                            "collections", "pathlib", "codeguard.models"},
    # 报告仍决定日志路径与呈现；私有原子落盘交给 storage，不称纯模型。
    "codeguard.reporting": {"__future__", "re", "json", "pathlib", "hashlib", "tempfile",
                           "codeguard.models", "codeguard.verdict", "codeguard.storage"},
    # scope 是已有文件物化适配器：注入配置/排除目录，尚未迁入内核包。
    "codeguard.planning": {"__future__", "collections", "pathlib", "scope", "codeguard.models"},
    "codeguard.git_syntax": {"__future__", "pathlib", "re", "shlex"},
    "codeguard.git_staging": {"__future__", "dataclasses", "os", "shlex", "pathlib",
                              "git_snapshot", "codeguard.git_syntax"},
    "codeguard.git_context": {"__future__", "dataclasses", "pathlib", "re", "shlex", "scope",
                             "codeguard.execution", "codeguard.git_syntax", "codeguard.git_staging"},
    "codeguard.path_policy": {"__future__", "fnmatch", "pathlib"},
    "codeguard.storage": {"__future__", "contextlib", "json", "os", "tempfile", "time",
                         "collections", "pathlib", "typing", "fcntl", "msvcrt"},
    "codeguard.hook_state": {"__future__", "contextlib", "hashlib", "os", "time",
                            "collections", "contextvars", "pathlib", "codeguard.storage", "codeguard.fingerprint"},
    "codeguard.cache": {"__future__", "contextlib", "hashlib", "time", "pathlib", "codeguard.storage"},
    "codeguard.fingerprint": {"__future__", "hashlib", "json", "os", "shutil", "stat", "pathlib",
                              "codeguard.execution"},
    "codeguard.baseline": {"__future__", "pathlib", "re", "tempfile", "codeguard.execution", "codeguard.verdict"},
    "codeguard.repository_policy": {"__future__", "os", "pathlib", "git_snapshot", "codeguard.execution",
                                    "codeguard.hook_state", "codeguard.path_policy"},
    "codeguard.spec_validation": {"__future__", "shutil", "pathlib", "codeguard.execution", "codeguard.reporting"},
    "codeguard.registry_schema": {"__future__", "re"},
    "codeguard.registry": {"__future__", "json", "pathlib", "typing", "codeguard.registry_schema"},
    "codeguard.config": {"__future__", "json", "re", "pathlib", "codeguard.registry"},
    "codeguard.discovery": {"__future__", "fnmatch", "re", "pathlib", "codeguard.config", "codeguard.path_policy", "codeguard.registry"},
    "codeguard.toolchain": {"__future__", "sys", "pathlib", "threading", "paths",
                                "codeguard.execution"},
    "codeguard.language_check": {"__future__", "pathlib", "codeguard.config", "codeguard.discovery",
                                  "codeguard.execution", "codeguard.models", "codeguard.planning",
                                  "codeguard.registry", "codeguard.storage", "codeguard.verdict",
                                  "codeguard.java_analysis"},
    "codeguard.check_application": {"__future__", "pathlib", "scope", "codeguard.config",
                                    "codeguard.discovery", "codeguard.fingerprint", "codeguard.java_analysis",
                                    "codeguard.language_check", "codeguard.registry", "codeguard.storage"},
    "codeguard.session_application": {"__future__", "collections.abc", "dataclasses", "pathlib",
                                      "codeguard.execution",
                                      "codeguard.hook_state", "codeguard.repository_policy",
                                      "codeguard.storage"},
    "codeguard.startup_application": {"__future__", "re", "dataclasses", "pathlib",
                                      "codeguard.config", "codeguard.discovery",
                                      "codeguard.registry", "codeguard.toolchain"},
    "codeguard.prompt_policy": {"__future__", "re"},
    "codeguard.prompt_application": {"__future__", "collections", "dataclasses", "pathlib",
                                     "codeguard.discovery", "codeguard.fingerprint", "codeguard.gate",
                                     "codeguard.hook_state", "codeguard.prompt_policy",
                                     "codeguard.registry", "codeguard.reporting",
                                     "codeguard.repository_policy"},
    "codeguard.git_guard_application": {"__future__", "collections", "dataclasses", "pathlib",
                                        "git_snapshot", "codeguard.gate", "codeguard.git_context",
                                        "codeguard.git_syntax", "codeguard.hook_state",
                                        "codeguard.reporting", "codeguard.repository_policy"},
    "codeguard.save_application": {"__future__", "hashlib", "tempfile", "collections",
                                   "dataclasses", "pathlib", "scope", "codeguard.hook_state",
                                   "codeguard.discovery", "codeguard.execution", "codeguard.fingerprint",
                                   "codeguard.planning", "codeguard.registry", "codeguard.storage",
                                   "codeguard.verdict"},
    "codeguard.java_build": {"__future__", "re", "xml", "pathlib"},
    "codeguard.java_impact": {"__future__", "collections", "pathlib"},
    "codeguard.java_planning": {"__future__", "collections"},
    "codeguard.java_changes": {"__future__", "re", "xml", "pathlib", "codeguard.execution", "codeguard.java_build"},
    "codeguard.java_environment": {"__future__", "os", "re", "sys", "xml", "pathlib",
                                   "codeguard.execution", "codeguard.java_build"},
    "codeguard.java_analysis": {"__future__", "json", "xml", "pathlib", "codeguard.config",
                                "codeguard.java_build", "codeguard.java_changes", "codeguard.java_environment",
                                "codeguard.java_impact", "codeguard.java_planning"},
    "codeguard.gate_checks": {"__future__", "pathlib", "codeguard.language_check", "codeguard.baseline",
                              "codeguard.discovery", "codeguard.registry", "codeguard.toolchain",
                              "codeguard.execution", "codeguard.models", "codeguard.planning",
                              "codeguard.reporting", "codeguard.verdict"},
    "codeguard.gate": {"__future__", "concurrent", "functools", "pathlib", "scope", "git_snapshot", "paths",
                       "codeguard.config", "codeguard.discovery", "codeguard.registry", "codeguard.toolchain",
                       "codeguard.cache", "codeguard.fingerprint", "codeguard.gate_checks", "codeguard.hook_state",
                       "codeguard.models", "codeguard.spec_validation"},
}


def _modules(root: Path) -> dict[str, Path]:
    modules = {}
    for folder in ("scripts", "hooks"):
        for path in sorted((root / folder).rglob("*.py")):
            parts = list(path.relative_to(root / folder).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            if parts:
                modules[".".join(parts)] = path
    return modules


def _imports(tree: ast.AST, name: str, package: bool, modules: dict[str, Path]):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parent = name.split(".") if package else name.split(".")[:-1]
                parent = parent[:len(parent) - node.level + 1]
                base = ".".join(parent + ([base] if base else []))
            children = [f"{base}.{alias.name}" for alias in node.names
                        if f"{base}.{alias.name}" in modules]
            if children:
                for child in children:
                    yield child, node.lineno
            else:
                yield base, node.lineno


def _local_module(target: str, modules: dict[str, Path]) -> str | None:
    # hooks 既可通过 sys.path 直接导入，也可按 namespace package 导入。
    if target.startswith(("scripts.", "hooks.")):
        target = target.split(".", 1)[1]
    parts = target.split(".")
    while parts:
        name = ".".join(parts)
        if name in modules:
            return name
        parts.pop()
    return None


def _cycles(graph: dict[str, set[str]]) -> list[str]:
    done: set[str] = set()
    active: list[str] = []
    found = []

    def visit(name):
        if name in active:
            found.append("cycle: " + " -> ".join(active[active.index(name):] + [name]))
            return
        if name in done:
            return
        active.append(name)
        for target in sorted(graph[name]):
            visit(target)
        active.pop()
        done.add(name)

    for name in sorted(graph):
        visit(name)
    return found


def check(root: Path) -> list[str]:
    """返回带位置的违例；范围涵盖 scripts/ 与 hooks/，不执行源码。"""
    modules = _modules(root)
    errors = []
    graph = {name: set() for name in modules}
    for name, path in modules.items():
        relative = path.relative_to(root).as_posix()
        if name.startswith("codeguard.") and name not in CORE_DEPENDENCIES:
            errors.append(f"{relative}:1: unclassified core module: {name}")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError, OSError) as exc:
            errors.append(f"{relative}: cannot parse: {exc}")
            continue
        allowed = CORE_DEPENDENCIES.get(name)
        for target, line in _imports(tree, name, path.name == "__init__.py", modules):
            local = _local_module(target, modules)
            if local:
                graph[name].add(local)
            if allowed is not None and target not in allowed and target.split(".")[0] not in allowed:
                errors.append(f"{relative}:{line}: forbidden dependency: {name} -> {target}")
    errors.extend(_script_roles(root, modules))
    return errors + _cycles(graph)


def _script_roles(root: Path, modules: dict) -> list[str]:
    """顶层 scripts/*.py 必须显式归类；compat-shim 必须带 Deprecated 通告；
    adapter 必须在 ADAPTER_LAYERS 声明用途。"""
    errors: list[str] = []
    top_level = {
        path.name
        for path in (root / "scripts").glob("*.py")
    }
    for name in sorted(top_level - set(SCRIPT_ROLES)):
        errors.append(f"scripts/{name}:1: unclassified top-level script (add to SCRIPT_ROLES)")
    # 完备性校验只对真实插件仓布局生效：架构用例会在合成临时树上跑本检查，
    # 临时树不需要携带全部顶层脚本，不应误报 missing。
    is_full_repo = (root / "scripts" / "check_architecture.py").is_file()
    if is_full_repo:
        for name in sorted(set(SCRIPT_ROLES) - top_level):
            errors.append(f"scripts/{name}:1: declared in SCRIPT_ROLES but missing on disk")
    for name, role in sorted(SCRIPT_ROLES.items()):
        path = root / "scripts" / name
        if not path.is_file():
            continue
        if is_full_repo and role == "compat-shim":
            head = path.read_text(encoding="utf-8")[:400]
            if "Deprecated" not in head:
                errors.append(f"scripts/{name}:1: compat-shim must carry a Deprecated notice in its docstring")
        if role == "adapter" and is_full_repo and name not in ADAPTER_LAYERS:
            errors.append(f"scripts/{name}:1: adapter must declare its purpose in ADAPTER_LAYERS")
    if is_full_repo:
        for name in sorted(set(ADAPTER_LAYERS) - top_level):
            errors.append(f"scripts/{name}:1: declared in ADAPTER_LAYERS but missing on disk")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if not (args.root / "scripts").is_dir():
        parser.error("目标缺少 scripts/，无法执行架构检查")
    errors = check(args.root)
    for error in errors:
        print(error)
    if not errors:
        print("Architecture OK: declared core dependencies and first-party import cycles checked")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
