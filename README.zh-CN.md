# 适用于 Codex 的 Switch Power

[English](README.md) · [Español](README.es.md) · [Русский](README.ru.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Switch Power 帮助 Codex 为每次请求选择执行方式。主对话会评估任务，在适合时委派给 Codex 原生子代理，核查结果，并在原对话中回复。即使在同一对话中，每条新请求也会重新评估。

统计文件数量可以使用 Luna 和 `low` 推理强度。视觉检查可以使用 Terra，复杂审计可以使用 Sol。选择取决于可用模型、工具、任务难度和出错成本。Sol、Terra 和 Luna 的 `low`、`medium`、`high` 已获预授权。使用 Astra 或高于 `high` 的推理强度，需要用户明确同意当前任务及其范围。

## 安装

0.1.2 版需要 Python 3.11 或更高版本，以及支持 `plugin marketplace`、`plugin add` 和 `model/list`、`skills/list`、`hooks/list` 方法的 Codex CLI。请在仓库根目录或解压后的 ZIP 目录中运行命令。

**macOS 和 Linux**

```bash
python3 scripts/setup.py
```

**Windows（PowerShell，原生 Codex）**

```powershell
py -3 scripts/setup.py
```

如果 Python 命令为 `python`，可用它替换 `py -3`。如果安装程序找不到 Codex，请通过 `--codex` 指定 `codex.exe` 的完整路径。添加 `--coordinator` 可以将协调代理的默认配置设为 GPT‑6.1 Sol 和 `high`。

安装后，在 Codex CLI 中打开 `/hooks`，查看 Switch Power 的 hook，并批准要启用的 hook。然后启动新的 Codex 会话。安装程序会在用户配置中注册插件，并在全局 `AGENTS.md` 或 `AGENTS.override.md` 中添加受管理的配置块。

## 使用

直接向 Codex 提出普通请求，例如“统计 `scripts/` 中的 `.py` 文件”。协调代理会直接完成简短的读取、计数和比较。当预期收益足以覆盖启动和核查成本，或你明确要求使用子代理时，它才会委派任务。在已验证的 V2 工具接口中，显式指定模型和推理强度时使用 `fork_turns: "none"`，协调代理会在任务说明中提供必要上下文。主对话模型由 Codex 管理。

## 模型和令牌用量

Switch Power 0.1.4 在回复后发出一条 Codex 提示，列出协调代理及可归属子代理的模型和令牌总数。请在应用的 **Settings → Hooks** 或 CLI 的 `/hooks` 中批准新的 hook。数据不全时，提示会显示 `partial` 或 `token usage unavailable`。提示的位置取决于 Codex 客户端。[实测结果和复现步骤](docs/usage-benchmark.md)。

在六组新的对照测试中，0.1.4 的总令牌用量比单独使用 Sol/high 少 11.0%。插件直接完成了所有任务。

## 停用和卸载

在项目目录中执行 `python3 scripts/install.py disable` 即可停用插件。将 `disable` 换成 `enable` 可重新启用，换成 `remove` 可卸载。在 Windows 上用 `py -3` 替换 `python3`。使用 `scripts/configure.py restore` 单独恢复协调代理原先的模型和推理强度。

0.1.2 版已通过 31 项测试，并在 macOS 上完成全新安装验证。原生 Windows Codex 的端到端验证仍待完成。详细信息见[验证报告](docs/verification.zh-CN.md)和[架构文档](docs/architecture.zh-CN.md)。
