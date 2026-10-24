# CodeGuard CLI 命令契约设计

## 1. 目标

让用户只记住少量稳定动词，同时保持 CodeGuard 独立安装、独立版本、独立 Hook。

## 2. 分层

生命周期：install、uninstall、upgrade、version、doctor、status、completion。
项目事实：discover、init、check、report。
专业命令：install,uninstall,upgrade,version,doctor,status,discover,init,check,fix,cve,dockerfile,impact,explain,report,hooks install,hooks status,engine,completion。

## 3. 语义

- install 只接宿主，不写项目。
- init 只写项目配置/基线，幂等，支持 --dry-run。
- hooks install 只写当前仓库 Git Hook。
- discover 只读识别。
- check 只读门禁，不自动修复。
- apply/fix 必须显式批准。
- doctor 诊断环境，不检查代码。
- status 读取状态，不重新执行。
- report 读取已有证据，不重新执行。

## 4. 输出与退出码

统一 JSON：schemaVersion、tool、command、decision、exitCode、findings、evidence、nextActions。
退出码：0 PASS，1 BLOCK，2 用法/配置错误，3 UNVERIFIED/DESIGN_ONLY，4 内部错误或运行时缺失。

## 5. Hook

CodeGuard 只调用自身命令。事件所有权：GitGuard 管 git commit/push；CodeGuard 管 Write/Edit 后的增量检查；FlowGuard 管阶段上下文；其他工具只做自身诊断和摘要。

## 6. 边界

没有真实执行证据时不得输出 PASS。CodeReview 使用 ocr 的真实命令，不伪造自有 CLI。
