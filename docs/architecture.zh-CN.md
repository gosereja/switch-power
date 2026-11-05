# Switch Power 架构

协调代理在主对话中接收请求。需要委派时，它将当前模型目录与可用启动工具的接口定义进行核对，然后选择执行代理和推理强度，明确工作范围，验证授权，并使用原生工具启动子代理。结果检查和最终回复均在原对话中完成。

| 组件 | 用途 |
| --- | --- |
| [`skills/coordinate`](../plugins/switch-power/skills/coordinate/SKILL.md) | 选择执行代理、协调任务和检查结果。 |
| [`scripts/policy.py`](../plugins/switch-power/scripts/policy.py) | 检查模型可用性、授权及工作范围。 |
| [`scripts/runtime.py`](../plugins/switch-power/scripts/runtime.py) | 原生模型目录、本地任务状态和验证 CLI。 |
| [`hooks/guard.py`](../plugins/switch-power/hooks/guard.py) | 处理 Codex 生命周期事件，并通过 `PreToolUse` 检查启动请求。 |
| [`scripts/install.py`](../scripts/install.py) | 全局安装、停用和卸载。 |
| [`scripts/configure.py`](../scripts/configure.py) | 配置或恢复主对话的模型。 |

## 任务生命周期

1. 协调代理直接处理简短的本地工作。委派前，它会评估收益能否覆盖准备、子代理执行和验证的成本。用户明确要求启动子代理时，仍需执行常规授权检查。
2. 准备委派时，CLI 登记任务和子代理的工作范围。Codex 接口支持时，原生调用显式指定模型及推理强度。
3. Astra 或高于 `high` 的强度均需用户同意具体模型、强度和工作范围。授权仅适用于当前任务。独立任务开启新的流程。
4. 协调代理通过原生生命周期获取结果，核对后回复。`finish` 命令清除任务状态。

主模型由 Codex 配置决定。具体委派任务通过原生子代理参数选择执行者。主对话接收下一条请求并重新评估。

已验证的 Codex V2 接口使用 `fork_turns: "none"` 来显式指定模型与推理强度。协调代理在任务说明中提供必要的上下文、约束和验收标准。

## 目录和状态

安装程序通过 `model/list` 获取模型目录。CLI 在准备委派时刷新过期数据，并检查数据是否有效及其与当前启动接口的兼容性。

任务状态保存在用户私有临时目录中，记录工作范围和最近一次请求，以便将授权与请求关联。模型目录单独保存在 Codex 配置目录中。[运行时命令参考](../plugins/switch-power/skills/coordinate/references/runtime.md)。

## 故障排查

在克隆目录或解压后的目录中执行 `python3 scripts/verify_native.py`。在 Windows 上使用 `py -3 scripts/verify_native.py`。该命令检查两个目录中的技能发现和 hook 状态。如果所需 hook 显示为 `untrusted`，请在 Codex CLI 中通过 `/hooks` 检查其定义。原生启动失败时，协调代理会说明原因并选择可用的处理方式。

Hook 的覆盖范围取决于 Codex 中的工具调用路径。任务边界和用户授权的语义由协调代理判断。[验证报告](verification.zh-CN.md)。
