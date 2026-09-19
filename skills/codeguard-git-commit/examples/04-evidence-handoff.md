# 证据交接

用户：把结果交给下一个处理人。

输出包含：目标范围、基线、真实命令/检查点、版本、退出码/风险、已做变更、复验、未完成与剩余风险。

执行原则：读取 git diff --cached 和最近提交风格，再校验 type、scope、subject、body 和 breaking change。
