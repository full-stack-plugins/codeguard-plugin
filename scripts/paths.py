"""scripts/paths.py：进程 PATH 补齐（hook 子进程环境修复）。

仅暴露 `ensure_user_path(from_login_shell=False)`。无业务依赖，被 hooks 与
tests 共享；与 `scripts/user_config.py`、`scripts/detect_lang.py` 同级但互不依赖。

为保持向后兼容，`scripts/detect_lang.py` 顶部 re-export 该符号，外部调用方
继续 `from detect_lang import ensure_user_path` 即可。
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def ensure_user_path(from_login_shell: bool = False) -> None:
    """补齐 hook 进程的 PATH。

    ZCode 等桌面宿主以 GUI 方式启动，hook 子进程继承的 PATH 往往缺少
    用户级工具目录（pip --user → ~/.local/bin、cargo → ~/.cargo/bin、
    nvm/fnm 的 node、homebrew），导致已安装的 linter 被误报「未安装」。

    始终补充常见静态目录；from_login_shell=True 时额外从用户登录 shell
    继承完整 PATH（覆盖 nvm 等动态目录，约 100-300ms，只适合低频钩子）。
    """
    static_dirs = [
        # 运行本进程的解释器自己的 bin 目录：ruff 等工具常装在这里
        # （anaconda、python -m pip install 等），不补就会"装了却报不在 PATH"。
        str(Path(sys.executable).parent),
        "/opt/homebrew/bin", "/usr/local/bin",
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / ".cargo" / "bin"),
        str(Path.home() / "go" / "bin"),
        str(Path.home() / ".local" / "pipx" / "bin"),
    ]
    cur = os.environ.get("PATH", "")
    parts = cur.split(os.pathsep)
    for d in reversed(static_dirs):
        if Path(d).exists() and d not in parts:
            parts.insert(0, d)
    os.environ["PATH"] = os.pathsep.join(parts)

    # node/npx 不可用且静态目录未覆盖时，自动降级登录 shell 继承一次
    # （覆盖 nvm/fnm/Kimi runtime 等非标准 node 安装；约 100-300ms）
    def _node_available() -> bool:
        return any(
            d and (Path(d) / "node").exists()
            for d in os.environ.get("PATH", "").split(os.pathsep)
        )

    if not from_login_shell and not _node_available():
        ensure_user_path(from_login_shell=True)
        return

    if not from_login_shell:
        return
    # 登录 shell 继承结果缓存（跨进程文件，10 分钟 TTL）——
    # 每条含触发词的消息/每次门禁都要补 PATH，不缓存则每次 spawn zsh（100-300ms）
    import time as _time
    cache_file = Path(tempfile.gettempdir()) / f"codeguard-path-cache-{os.getuid()}"
    now = _time.time()
    if cache_file.exists():
        try:
            age = now - cache_file.stat().st_mtime
            cached = cache_file.read_text().strip()
            if age < 600 and os.pathsep in cached:
                os.environ["PATH"] = cached
                return
        except OSError:
            pass
    try:
        shell = os.environ.get("SHELL") or "/bin/zsh"
        proc = subprocess.run(
            [shell, "-lc", "printf '%s' \"$PATH\""],
            capture_output=True, check=False, text=True, timeout=5,
        )
        if proc.returncode == 0:
            inherited = proc.stdout.strip().splitlines()
            if inherited:
                # 即使登录 shell 没提供更丰富的 PATH，也缓存这次探测结果。
                # Linux CI 的 login shell 常与当前 PATH 等价；若不写缓存，
                # 每次钩子都会重复 spawn shell，违背十分钟缓存契约。
                resolved = inherited[-1] if inherited[-1].count(os.pathsep) > cur.count(os.pathsep) else os.environ["PATH"]
                os.environ["PATH"] = resolved
                with contextlib.suppress(OSError):
                    cache_file.write_text(resolved)
    except (OSError, subprocess.SubprocessError):
        pass
