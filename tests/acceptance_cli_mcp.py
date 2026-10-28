"""Explicit Linux acceptance with real Ruff, MCP stdio and the default Hook.

Run with a Python environment containing requirements.txt and requirements-dev.txt:
    python tests/acceptance_cli_mcp.py --output /absolute/evidence.json
No hosted agent is invoked. All project/cache/install writes use a temporary directory.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PLUGIN = Path(__file__).resolve().parents[1]


async def accept() -> dict:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("This acceptance script covers Linux x64 only")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
           "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}
    for tool in ("ruff", "node", "git", "bash"):
        if not shutil.which(tool, path=env["PATH"]):
            raise RuntimeError(f"Required real tool missing: {tool}")
    evidence = {"scope": "Linux x64 Python compatibility CLI/MCP and default Hook rejection",
                "host_acceptance": False, "rust_plugin_execution": False, "observations": []}
    observations = evidence["observations"]
    with tempfile.TemporaryDirectory(prefix="codeguard-live-acceptance-") as temporary:
        root = Path(temporary)
        project = root / "project"
        project.mkdir()
        env["CODEGUARD_HOME"] = str(root / "state")
        env["CODEGUARD_RUNTIME_CACHE"] = str(root / "runtime")

        def run(args, *, input_text=None):
            result = subprocess.run(args, cwd=project, env=env, input=input_text,
                                    text=True, capture_output=True, timeout=30, check=False)
            return result

        assert run(["git", "init", "--quiet"]).returncode == 0
        (project / "pyproject.toml").write_text('[tool.ruff]\nline-length = 88\n')
        source = project / "sample.py"
        source.write_text("import os\n")
        install = run([str(PLUGIN / "bin/codeguard"), "install", "--bin-dir", str(root / "bin")])
        assert install.returncode == 0, install.stderr
        cli = root / "bin/codeguard"
        bad = run([str(cli), "check", "--lang", "python", str(project)])
        assert bad.returncode == 2, bad.stdout + bad.stderr
        assert source.read_text() == "import os\n", "check modified source"
        observations.append({"entry": "installed-cli", "scenario": "real-ruff-finding",
                             "exit": bad.returncode, "stdout": bad.stdout})

        manifest = json.loads((PLUGIN / "mcp.json").read_text())["mcpServers"]["codeguard"]
        params = StdioServerParameters(command=manifest["command"], args=manifest["args"],
                                       cwd=str(PLUGIN), env=env)
        async with (stdio_client(params) as (read, write),
                    ClientSession(read, write) as session):
            await session.initialize()
            tools = await session.list_tools()
            assert "check_code_style" in [tool.name for tool in tools.tools]

            async def call(name, arguments):
                response = await session.call_tool(name, arguments)
                assert not response.isError, response
                return json.loads(response.content[0].text)

            languages = await call("list_languages", {})
            assert len(languages) == 57, len(languages)
            evidence["language_validation"] = [
                {"id": language["id"], "registration": "present",
                 "current_run": "real_ruff_cli_and_mcp" if language["id"] == "python" else "not_exercised"}
                for language in languages
            ]
            observations.append({"entry": "mcp-stdio", "registered_languages": len(languages)})
            arguments = {"path": str(project), "languages": ["python"]}
            failing = await call("check_code_style", arguments)
            assert failing[0]["status"] == "FAIL" and not failing[0]["passed"], failing
            log = Path(failing[0]["log_path"])
            assert log.is_relative_to(project) and "F401" in log.read_text(), failing
            observations.append({"entry": "mcp-stdio", "scenario": "real-ruff-finding", "result": failing})
            (project / "codeguard.json").write_text("{")
            invalid = await call("check_code_style", arguments)
            assert invalid["status"] == "UNVERIFIED" and not invalid["passed"], invalid
            observations.append({"entry": "mcp-stdio", "scenario": "bad-config", "result": invalid})
            (project / "codeguard.json").write_text("{}")
            source.write_text("value = 1\n")
            clean = await call("check_code_style", arguments)
            assert clean[0]["status"] == "PASS" and clean[0]["passed"], clean
            observations.append({"entry": "mcp-stdio", "scenario": "same-session-recovery", "result": clean})
            assert source.read_text() == "value = 1\n", "check modified source"

        good = run([str(cli), "check", "--lang", "python", str(project)])
        assert good.returncode == 0, good.stdout + good.stderr
        observations.append({"entry": "installed-cli", "scenario": "real-ruff-clean", "exit": good.returncode})
        hook = run(["node", str(PLUGIN / "hooks/rust_runtime_dispatch.cjs"), "session-start"],
                   input_text=json.dumps({"hook_event_name": "SessionStart", "cwd": str(project), "source": "startup"}))
        assert hook.returncode == 0, hook.stderr
        feedback = json.loads(hook.stdout)
        message = feedback["hookSpecificOutput"]["additionalContext"]
        assert "platform_unsupported" in message and "本次源码检查未运行" in message, message
        assert not (root / "runtime").exists(), "unsupported Hook created runtime cache"
        observations.append({"entry": "default-hook", "scenario": "unsupported-linux",
                             "exit": hook.returncode, "response": feedback})
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    async def bounded_acceptance():
        return await asyncio.wait_for(accept(), timeout=120)

    evidence = asyncio.run(bounded_acceptance())
    arguments.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(f"Acceptance passed; scoped evidence: {arguments.output}")
