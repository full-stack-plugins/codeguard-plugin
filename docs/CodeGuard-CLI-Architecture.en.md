# CodeGuard CLI Architecture

## 1. Positioning

CodeGuard（代码质量防护）是独立 CLI，不依赖统一 guard 调度器。插件只负责宿主集成、Hook 和技能路由。

## 2. Command layers

生命周期：install/uninstall/upgrade/version/doctor/status/completion。
项目事实：discover/init/check/report。
专业命令：install,uninstall,upgrade,version,doctor,status,discover,init,check,fix,cve,dockerfile,impact,explain,report,hooks install,hooks status,engine,completion。

## 3. State and evidence

项目状态写入 .guard/evidence/codeguard/；配置由各工具管理。FlowGuard 只读证据，不替其他工具执行。

## 4. Security

install 不写项目，init 不写宿主，hooks install 不静默执行。所有写操作支持 --dry-run/--yes。

## 5. Maturity

已实现 check/fix/cve/dockerfile/detect/engine/init(引导)
