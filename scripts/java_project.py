"""Java 项目感知：只读构建描述，计算模块反向依赖闭包，不执行构建或索引。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
                "settings.gradle.kts", "gradle.properties", "mvnw", "gradlew", "codeguard.json"}


def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"构建路径在仓外: {path}")
    return resolved


def _text(node, path: str, default="") -> str:
    return node.findtext(path, default=default).strip()


def _maven(root: Path) -> tuple[dict, list[str]]:
    modules: dict = {}
    reasons: list[str] = []

    def visit(directory: Path, inherited: dict):
        directory = _inside(root, directory)
        name = directory.relative_to(root).as_posix()
        if name in modules:
            return
        doc = ET.parse(_inside(root, directory / "pom.xml")).getroot()
        props = dict(inherited)
        properties = doc.find("{*}properties")
        if properties is not None:
            props.update({p.tag.split("}")[-1]: (p.text or "").strip() for p in properties})

        def expand(value: str) -> str:
            for _ in range(10):
                newer = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m[1], m[0]), value)
                if newer == value:
                    break
                value = newer
            if "${" in value:
                reasons.append(f"{name}: 无法静态解析 {value}，回退全模块")
            return value

        group = expand(_text(doc, "{*}groupId") or _text(doc, "{*}parent/{*}groupId")
                       or props.get("project.groupId", ""))
        artifact = expand(_text(doc, "{*}artifactId"))
        if not artifact:
            raise ValueError(f"{name}: 缺少 artifactId")
        props.update({"project.groupId": group, "pom.groupId": group,
                      "project.artifactId": artifact})
        dependencies = []
        for dep in doc.findall("{*}dependencies/{*}dependency"):
            dependencies.append((expand(_text(dep, "{*}groupId")), expand(_text(dep, "{*}artifactId"))))
        plugins = [p.text or "" for p in doc.findall("{*}build/{*}plugins/{*}plugin/{*}artifactId")]
        modules[name] = {"path": name, "coordinate": (group, artifact),
                         "raw_dependencies": dependencies, "dependencies": [], "plugins": plugins}
        if doc.find("{*}profiles") is not None:
            reasons.append(f"{name}: Maven profiles 可能改变模块/依赖，回退根 verify")
        if dependencies and doc.findall("{*}modules/{*}module"):
            reasons.append(f"{name}: 聚合父 POM 依赖可能被子模块继承，回退根 verify")
        for child in doc.findall("{*}modules/{*}module"):
            visit(directory / expand((child.text or "").strip()), props)

    visit(root, {})
    coordinates = {}
    for name, module in modules.items():
        coordinate = module["coordinate"]
        if coordinate in coordinates:
            reasons.append("模块坐标不唯一，回退全模块")
        coordinates[coordinate] = name
    for module in modules.values():
        module["dependencies"] = sorted({coordinates[d] for d in module.pop("raw_dependencies") if d in coordinates})
        module.pop("coordinate")
    return modules, reasons


def _gradle(root: Path) -> tuple[dict, list[str]]:
    reasons = []
    modules = {".": {"path": ".", "dependencies": [], "plugins": []}}
    settings = next((p for p in (root / "settings.gradle.kts", root / "settings.gradle") if p.exists()), None)
    if settings:
        body = _inside(root, settings).read_text()
        includes = re.findall(r"\binclude\s*(\([^)]*\)|[^\n]+)", body)
        for expression in includes:
            literals = re.findall(r"['\"](:?[\w:-]+)['\"]", expression)
            residue = re.sub(r"['\"](:?[\w:-]+)['\"]|[\s,()]", "", expression)
            if not literals or residue:
                reasons.append("Gradle include 使用动态表达式，回退根 check")
            for literal in literals:
                name = literal.lstrip(":").replace(":", "/")
                _inside(root, root / name)
                modules[name] = {"path": name, "dependencies": [], "plugins": []}
        if re.search(r"includeBuild|projectDir|apply\s|\bfor\s*\(|\.each\b", body):
            reasons.append("Gradle settings 存在动态/复合构建，回退根 check")
    for name, module in modules.items():
        directory = _inside(root, root / name)
        build = next((p for p in (directory / "build.gradle.kts", directory / "build.gradle") if p.exists()), None)
        if not build:
            reasons.append(f"{name}: 没有可读取的 Gradle 构建描述，回退根 check")
            continue
        body = _inside(root, build).read_text()
        references = re.findall(r"\bproject\s*\(\s*(?:path\s*[:=]\s*)?['\"](:[\w:-]+)['\"]\s*\)", body)
        module["dependencies"] = sorted({r.lstrip(":").replace(":", "/") for r in references})
        if any(d not in modules for d in module["dependencies"]):
            reasons.append(f"{name}: 引用了未声明项目，回退根 check")
        if len(re.findall(r"\bproject\s*\(", body)) != len(references) or re.search(
                r"apply\s+from|apply\s*\(\s*from|subprojects|allprojects|buildSrc|\bprojects\.|\bif\s*\(|\bfor\s*\(", body):
            reasons.append(f"{name}: Gradle 动态构建无法可靠缩小范围，回退根 check")
    if (root / "buildSrc").exists():
        reasons.append("存在 buildSrc 构建逻辑，回退根 check")
    return modules, reasons


def _resolve_java_home(root: Path) -> tuple[str | None, str | None]:
    """解析 pom/java.version 并找到兼容 JDK；返回 (JAVA_HOME 路径, 原因)。

    逻辑：
    1. 从 pom.xml 的 <java.version> 或 <maven.compiler.release> 读取版本号
    2. 在 macOS 用 `/usr/libexec/java_home -v <ver>` 查找；在 Linux 用
       `update-alternatives --list java` 匹配
    3. 找到则返回 JAVA_HOME 路径（调用方注入 lint 子进程）；
       找不到则返回 (None, "需要 JDK X，已装列表：…")——调用方将此作为
       UNVERIFIED 理由，而非 FAIL。
    """
    import subprocess
    java_version = None
    pom = root / "pom.xml"
    if pom.is_file():
        try:
            content = pom.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"<java\.version>\s*(\d+)", content) or \
                re.search(r"<maven\.compiler\.release>\s*(\d+)", content)
            if m:
                java_version = int(m.group(1))
        except OSError:
            pass
    if java_version is None:
        return None, None  # 未声明版本——用默认 JDK，不干预
    # macOS: /usr/libexec/java_home -v <ver>
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["/usr/libexec/java_home", "-v", str(java_version)],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip(), None
        except (subprocess.TimeoutExpired, OSError):
            pass
    # Linux: update-alternatives --list java
    if sys.platform == "linux":
        try:
            result = subprocess.run(
                ["update-alternatives", "--list", "java"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    path = line.strip()
                    # 从路径提取版本号（如 /usr/lib/jvm/java-21-openjdk-amd64/bin/java）
                    vm = re.search(r"java[-.](\d+)", path)
                    if vm and int(vm.group(1)) == java_version:
                        home = str(Path(path).parent.parent)
                        return home, None
        except (subprocess.TimeoutExpired, OSError):
            pass
    # 未找到匹配 JDK
    return None, f"需要 JDK {java_version}，当前环境无匹配版本"


def _is_version_bump_only(root: Path, changed: list[str] | None) -> bool:
    """检测变更是否为纯版本 bump（只改 pom/build.gradle 的 version/revision 行）。

    用 git diff 对比变更文件的实际内容差异：新增/删除/修改的行都不含
    依赖、插件、模块结构等关键词时，判定为纯版本 bump。无需联网或
    构建——纯文本 diff 足以区分「改个版本号」与「改了依赖」。
    """
    import subprocess
    if not changed:
        return False
    build_names = {"pom.xml", "build.gradle", "build.gradle.kts"}
    for f in changed:
        if Path(f).name not in build_names:
            return False
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--"] + [str(f) for f in changed],
            cwd=str(root), capture_output=True, text=True, timeout=5, check=False,
        )
        diff = result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return False
    # 只看 +/- 行的实际内容（排除 diff 头）
    content_lines = [
        ln for ln in diff.splitlines()
        if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
    ]
    if not content_lines:
        return False
    # 纯版本 bump：变更行只涉及 version/revision/group/artifactId/description
    # 等坐标性字段，不含依赖/插件/模块/属性等结构关键词
    structural = re.compile(
        r"<(dependency|plugin|module|parent|properties|build|profile)|"
        r"implementation|api|testImplementation|compileOnly|runtimeOnly",
        re.IGNORECASE,
    )
    return not any(structural.search(ln) for ln in content_lines)


def analyze(project_root: str | Path, changed: list[str] | None = None) -> dict:
    """返回只读计划；changed=None 全量，[] 无变更；绝不把规划当成验证通过。"""
    root = Path(project_root).resolve()
    plan = {"status": "UNVERIFIED", "root": str(root), "build_system": None,
            "changed_paths": changed,
            "analysis_level": "module", "modules": [], "affected_modules": [], "commands": [],
            "conservative": False, "reasons": [], "gaps": ["模块依赖图不是完整符号/业务语义分析"]}
    try:
        if (root / "pom.xml").is_file():
            system, (modules, reasons) = "maven", _maven(root)
        elif any((root / n).is_file() for n in ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")):
            system, (modules, reasons) = "gradle", _gradle(root)
        else:
            raise ValueError("未找到 Maven/Gradle 构建描述")
        plan.update(build_system=system, modules=list(modules.values()))
        wrapper = "mvnw" if system == "maven" else "gradlew"
        if os.name == "nt":
            wrapper += ".cmd" if system == "maven" else ".bat"
        executable = "./" + wrapper if (root / wrapper).is_file() else ("mvn" if system == "maven" else "gradle")
        if (root / wrapper).exists() and os.name != "nt" and not os.access(root / wrapper, os.X_OK):
            raise ValueError(f"wrapper 不可执行: {wrapper}")
        # 顶层 executable 键：门禁消费者（gate_lib Java 门禁）直接读取，
        # 用于把 PATH 上的 mvn/gradle 替换为项目自带 wrapper——
        # POM 4.1.0 等 Maven 4 仓库在 Maven 3 下必然解析失败（实测）。
        plan["executable"] = executable
        relevant = None if changed is None else [p for p in changed if p.endswith((".java", ".kt", ".groovy", ".scala"))
                                                 or "/src/" in "/" + p
                                                 or Path(p).name in _BUILD_FILES or p.startswith((".mvn/", "gradle/"))]
        if relevant is not None:
            for name in relevant:
                _inside(root, root / name)
        full = relevant is None or bool(reasons) or any(
            Path(p).name in _BUILD_FILES or p.startswith((".mvn/", "gradle/")) for p in relevant or [])
        affected = set(modules) if full else set()
        if not full:
            for path in relevant or []:
                owners = [m for m in modules if m == "." or path.startswith(m + "/")]
                if owners:
                    affected.add(max(owners, key=len))
            # 反向传递闭包：改动依赖的模块必须重新验证。
            while True:
                expanded = affected | {m for m, detail in modules.items() if affected.intersection(detail["dependencies"])}
                if expanded == affected:
                    break
                affected = expanded
        if relevant == []:
            affected = set()
        commands = []
        if affected:
            # 纯版本 bump 提交（只改 pom/build.gradle 的 version/revision 行）
            # 降级为 validate/help 级——版本号变更不影响编译产物正确性，
            # 全量 verify 在大仓上每次 bump 都是分钟级浪费（实测发布流程痛点）。
            bump_only = _is_version_bump_only(root, changed)
            if system == "maven":
                argv = [executable, "-B"]
                if not full and "." not in affected:
                    argv += ["-pl", ",".join(sorted(affected)), "-am"]
                # 默认等级不含测试执行（-DskipTests 只跳执行，测试代码仍编译）：
                # 门禁管提交面的编译/打包/静态正确性，测试执行交 CI 或
                # codeguard.json java.commands 显式声明——大仓全量测试普遍超
                # 门禁超时预算，跑满也只剩 UNVERIFIED，反而给不出结论。
                argv += ["-DskipTests", "validate" if bump_only else "verify"]
            else:
                argv = [executable] + (["help"] if bump_only else
                                      ["check"] if full or "." in affected else
                                      [":" + p.replace("/", ":") + ":check" for p in sorted(affected)])
                if not bump_only:
                    argv += ["-x", "test"]
            commands = [{"kind": "verify", "argv": argv}]
            config = root / "codeguard.json"
            if config.exists():
                explicit = json.loads(_inside(root, config).read_text()).get("java", {}).get("commands")
                if explicit is not None:
                    if not isinstance(explicit, list) or not explicit or any(
                            not isinstance(c, list) or not c or any(not isinstance(a, str) or not a for a in c)
                            for c in explicit):
                        raise ValueError("java.commands 必须是非空 argv 数组列表")
                    commands = [{"kind": "configured", "argv": c} for c in explicit]
                    reasons.append("使用 codeguard.json 明确声明的权威检查命令")
        plugins = {p for m in modules.values() for p in m["plugins"]}
        if not plugins.intersection({"maven-checkstyle-plugin", "maven-pmd-plugin", "spotbugs-maven-plugin"}):
            plan["gaps"].append("未确认静态规则已绑定生命周期；verify/check 成功不代表 Checkstyle/PMD 全覆盖")
        # JDK 兼容性：解析 java.version 并查找可用 JDK；找到则注入 JAVA_HOME
        jdk_home, jdk_reason = _resolve_java_home(root)
        if jdk_home:
            for cmd in commands:
                cmd["env"] = {"JAVA_HOME": jdk_home}
            reasons.append(f"JAVA_HOME={jdk_home}")
        elif jdk_reason:
            reasons.append(jdk_reason)
        plan.update(status="PLANNED" if commands else "SKIPPED", commands=commands,
                    affected_modules=sorted(affected), conservative=bool(full and relevant is not None),
                    reasons=reasons or ["按构建模块及反向依赖闭包选择；命令尚未执行"])
    except (OSError, ValueError, TypeError, AttributeError, ET.ParseError) as exc:
        plan.update(status="UNVERIFIED", commands=[], reasons=[str(exc)])
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="只读 Java 项目与影响分析；不会执行构建或安装工具")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--changed", nargs="*", default=None, help="仓根相对路径；缺省全量")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()
    plan = analyze(args.path, args.changed)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"Java {plan['status']} | {plan['build_system']} | 模块级分析（未执行）")
        print("影响模块: " + ", ".join(plan["affected_modules"]))
        for command in plan["commands"]:
            import shlex
            print("计划命令: " + shlex.join(command["argv"]))
        print("说明: " + "；".join(plan["reasons"] + plan["gaps"]))
    return 1 if plan["status"] == "UNVERIFIED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
