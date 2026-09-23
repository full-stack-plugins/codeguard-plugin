# doc-behavior-parity Specification

## Purpose
把文档中的可执行断言钉在行为测试上：凡是文档声明的绕过语义、命令形态、默认忽略规则与退出码
契约，MUST 有测试与真实实现互证，使「文档与行为矛盾」在 CI 现形，而不是依赖会话考古发现。
## Requirements
### Requirement: Executable documentation claims SHALL be pinned by tests

文档中可机器判定的行为断言 MUST 有对应测试互证，至少覆盖：绕过豁免的值词表、命令行生态标识
与别名、点前缀默认忽略语义、markdown 探活命令形态、CVE 退出码契约。断言 MUST 从文档文本与
实现两侧取值比对（而非只测实现），使文档更新与行为变更脱节时测试变红。

#### Scenario: Documentation and behavior diverge

- **WHEN** 文档中的某条可执行断言（如退出码集合、别名集合）与实现不一致
- **THEN** 对应测试失败并点名该断言

#### Scenario: Documented bypass values match the parser

- **WHEN** gate 指令文案声明的豁免值词表与 env 解析器接受的词表不一致
- **THEN** 测试失败

