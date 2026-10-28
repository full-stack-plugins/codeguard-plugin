"""Real preinstalled Ruff/rustfmt acceptance in disposable repositories.
No installation, mock checker, network fetch or host configuration changes.
"""

import argparse
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plugin", type=pathlib.Path, required=True)
parser.add_argument("--output", type=pathlib.Path, required=True)
args = parser.parse_args()
plugin = args.plugin.resolve()
sys.path.insert(0, str(plugin / "scripts"))
from codeguard.language_check import run_check, run_fix

records = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv, cwd, expected=0):
    p = subprocess.run(
        [str(x) for x in argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        check=False,
    )
    assert p.returncode == expected, (argv, p.returncode, p.stdout, p.stderr)
    return {
        "argv": [str(x) for x in argv],
        "exit": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def cli(root, *arguments, expected=0):
    return command(
        [sys.executable, plugin / "scripts/cli_entry.py", *arguments, root],
        root,
        expected,
    )


def check(root, expected, timeout=120):
    result = run_check(["python"], root, timeout=timeout)[0]
    assert result["status"] == expected, result
    return result


def record(language, scenario, **data):
    records.append(dict(language=language, scenario=scenario, **data))


os.environ.update(
    CARGO_NET_OFFLINE="true", RUFF_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"
)
versions = {
    name: command(cmd, plugin)
    for name, cmd in [
        ("ruff", ["ruff", "--version"]),
        ("rustfmt", ["cargo", "fmt", "--version"]),
    ]
}
assert versions["ruff"]["stdout"].startswith("ruff 0.16.8"), versions
assert versions["rustfmt"]["stdout"].startswith("rustfmt "), versions
with tempfile.TemporaryDirectory(prefix="guard-real-language-batch-") as temporary:
    base = pathlib.Path(temporary).resolve()
    os.environ["CODEGUARD_HOME"] = str(base / "state")
    py = base / "python"
    py.mkdir()
    command(["git", "init", "--quiet", py], base)
    source = py / "sample.py"
    cfg = py / "pyproject.toml"
    valid = '[tool.ruff.lint]\nselect = ["F"]\n'
    cfg.write_text(valid)
    source.write_text("value = 1\n")
    before = digest(source)
    record(
        "python",
        "correct_input",
        result=check(py, "PASS"),
        cli=cli(py, "check", "--lang", "python"),
        unchanged=digest(source) == before,
    )
    source.write_text("import os\n\nvalue = 1\n")
    before = digest(source)
    failure = check(py, "FAIL")
    assert "F401" in failure["stdout_tail"], failure
    record(
        "python",
        "violation",
        result=failure,
        cli=cli(py, "check", "--lang", "python", expected=2),
        unchanged=digest(source) == before,
    )
    dry = cli(py, "fix", "--all", "--lang", "python", "--dry-run")
    assert digest(source) == before
    record("python", "dry_run_no_write", cli=dry, sha256=before)
    fixed = cli(py, "fix", "--all", "--lang", "python")
    after = digest(source)
    assert after != before and "import os" not in source.read_text()
    record(
        "python",
        "registered_autofix",
        cli=fixed,
        before_sha256=before,
        after_sha256=after,
        recheck=check(py, "PASS"),
        meaning="ruff check --fix; not ruff format style formatting",
    )
    repeat = cli(py, "fix", "--all", "--lang", "python")
    assert digest(source) == after
    record("python", "second_fix_idempotent", cli=repeat, sha256=after)
    cfg.write_text("[tool.ruff]\nselect = [\n")
    bad_config = check(py, "UNVERIFIED")
    repair = run_fix(["python"], py)[0]
    assert (
        repair["fixed"] is False
        and repair["exit_code"] != 0
        and digest(source) == after
    ), repair
    record(
        "python",
        "invalid_checker_configuration",
        result=bad_config,
        fix=repair,
        unchanged=True,
    )
    cfg.write_text(valid)
    record("python", "configuration_recovery", result=check(py, "PASS"))
    # Real Ruff scanning fresh files, with an explicitly expired budget. No fake
    # executable/sleep wrapper; this tests timeout classification, not throughput.
    corpus = py / "timeout_corpus"
    corpus.mkdir()
    for number in range(512):
        (corpus / f"case_{number}.py").write_text("value = 1\n" * 200)
    start = time.monotonic()
    timed = check(py, "UNVERIFIED", timeout=0)
    assert timed["exit_code"] == 124 and "timeout" in timed["stderr_tail"], timed
    assert digest(source) == after
    record(
        "python",
        "expired_budget_real_checker",
        result=timed,
        elapsed_seconds=time.monotonic() - start,
        read_only_source_unchanged=True,
        budget_seconds=0,
        corpus_files=512,
    )
    # One tiny dependency-free Rust crate exercises the configured formatter.
    rs = base / "rust"
    rs.mkdir()
    command(["git", "init", "--quiet", rs], base)
    manifest = rs / "Cargo.toml"
    cargo = '[package]\nname = "guard_format_acceptance"\nversion = "0.1.0"\nedition = "2021"\n'
    manifest.write_text(cargo)
    (rs / "src").mkdir()
    rust = rs / "src/main.rs"
    rust.write_text('fn main(){let value=1;println!("{}",value);}\n')
    before = digest(rust)
    oracle = command(["cargo", "fmt", "--all", "--", "--check"], rs, 1)
    assert digest(rust) == before
    record(
        "rust",
        "format_violation",
        oracle=oracle,
        unchanged=True,
        scope="real formatter check, not Clippy lint",
    )
    fixed = cli(rs, "fix", "--all", "--lang", "rust")
    after = digest(rust)
    assert after != before
    record(
        "rust",
        "registered_formatter",
        cli=fixed,
        before_sha256=before,
        after_sha256=after,
        oracle=command(["cargo", "fmt", "--all", "--", "--check"], rs),
    )
    repeat = cli(rs, "fix", "--all", "--lang", "rust")
    assert digest(rust) == after
    record("rust", "second_format_idempotent", cli=repeat, sha256=after)
    manifest.write_text("[package\n")
    bad = run_fix(["rust"], rs)[0]
    assert bad["fixed"] is False and bad["exit_code"] != 0 and digest(rust) == after, (
        bad
    )
    record("rust", "invalid_manifest", result=bad, unchanged=True)
    manifest.write_text(cargo)
    rust.write_text("fn main( {\n")
    before = digest(rust)
    syntax = run_fix(["rust"], rs)[0]
    assert (
        not syntax["fixed"] and syntax["exit_code"] != 0 and digest(rust) == before
    ), syntax
    record("rust", "invalid_syntax_no_success", result=syntax, unchanged=True)
    rust.write_text("fn main() {}\n")
    recovery = run_fix(["rust"], rs)[0]
    assert recovery["fixed"]
    record(
        "rust",
        "formatter_recovery",
        result=recovery,
        oracle=command(["cargo", "fmt", "--all", "--", "--check"], rs),
    )

sha = command(["git", "rev-parse", "HEAD"], plugin)["stdout"].strip()
paths = [
    "scripts/languages.json",
    "scripts/scope.py",
    "scripts/codeguard/language_check.py",
    "scripts/codeguard/execution.py",
    "scripts/codeguard/verdict.py",
    "scripts/fix.py",
    "scripts/run_check.py",
    "scripts/cli_entry.py",
]
assert all(record.get("unchanged", True) for record in records), records
checked_paths = [
    "scripts",
    "tests",
    "linters",
    "requirements.txt",
    "requirements-dev.txt",
    ".github/workflows/cli-install-candidate.yml",
]
changes = command(["git", "status", "--porcelain", "--", *checked_paths], plugin)[
    "stdout"
]
evidence = {
    "status": "passed",
    "plugin_commit": sha,
    "checked_source_paths_clean": not bool(changes.strip()),
    "checked_source_paths": checked_paths,
    "plugin_changes": changes.splitlines(),
    "platform": platform.platform(),
    "machine": platform.machine(),
    "tools": versions,
    "records": records,
    "product_source_hashes": {p: digest(plugin / p) for p in paths},
    "harness_sha256": digest(pathlib.Path(__file__)),
    "notes": [
        "Python format registration is lint autofix, not standalone Ruff format.",
        "Rust checker Clippy was not exercised in this batch.",
        "Timeout used real Ruff and an intentionally zero budget; not a performance benchmark.",
        "No other languages or host/platform combinations are inferred.",
    ],
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
print(
    json.dumps(
        {
            "status": "passed",
            "scenarios": len(records),
            "languages": ["python", "rust"],
            "output": str(args.output),
        },
        ensure_ascii=False,
    )
)
