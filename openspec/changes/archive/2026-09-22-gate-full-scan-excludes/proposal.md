# 2026-09-22-gate-full-scan-excludes

## Why

ddd4j-boot 13 分支仓实测：java 门禁 `mvn javadoc:jar` 在 `target/**/apidocs/`
生成无 shebang 的 `javadoc.sh`，shell 门禁的 find 把它当源码扫（SC2148），
commit/push 门禁必红且删了也输（java lint 并发再生成）——两个 gate 步骤
互相矛盾。排除基建已存在但只物化 ruff：`scope_cmd(full_excludes=True)`
仅对 `ruff` 追加 `--exclude`，`find -print0` 型 gate 原样透传。同批实测
还发现：老发布版本 shellcheck gate 缺 `--severity` 钉扎，info 级发现
（SC2059/SC2295）也阻塞；skipGate 豁免只有总数没有明细。

## What Changes

- `scope.py`：`_RUFF_FULL_EXCLUDES` → 公开的 `FULL_SCAN_EXCLUDES`（单一
  事实源）；新增 `_inject_find_excludes`——`full_excludes=True` 时给
  `find … -print0` 型命令注入 `-not -path '*/<dir>/*'`，幂等，ruff 路径不变。
- `gate_lib.py`：delta 超 50 文件回退全量命令的路径补 `full_excludes=True`
  （回退路径此前比常规全量门禁更容易扫到 target/）；java 门禁依赖解析
  失败（Could not resolve / Could not find artifact）追加行动指引；
  `record_skip_event` 增加最近 20 条明细（时间 + 仓库 + 类型），总数与
  kinds 字段保持兼容。
- `validate_languages_json.py`：新契约——gate/lint 中调用 shellcheck 必须
  钉扎 `--severity=`（防"门禁结论随 cache 版本漂移"回归）。

## Impact

- Affected specs: `language-gate-commands`（gate 命令可执行性 + 一致性契约）
- 受益场景：任何 Maven/Gradle 项目（构建产物不再引发 shell/java 门禁互斥）、
  skipGate 豁免可回溯、依赖解析失败有出路指引。
