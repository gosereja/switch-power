# Switch Power for Codex

[English](README.md) · [Español](README.es.md) · [Русский](README.ru.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Switch Power helps Codex choose how to execute each request. The main chat assesses the work, delegates to native subagents when useful, checks their results, and replies in the same conversation. It reassesses each new request, even in an existing chat.

Counting files can suit Luna with `low` reasoning. A visual review can suit Terra, and a complex audit can suit Sol. The coordinator considers model availability, tool access, ambiguity, and the cost of errors. It can answer short conversational questions directly. Sol, Terra, and Luna with `low`, `medium`, or `high` effort are preapproved. Astra and effort above `high` require explicit consent for the current task and scope.

## Install

Version 0.1.2 requires Python 3.11+ and Codex CLI with `plugin marketplace`, `plugin add`, and app-server methods `model/list`, `skills/list`, and `hooks/list`. Run the command from the repository root or the extracted `switch-power-0.1.2.zip` directory.

**macOS and Linux**

```bash
python3 scripts/setup.py
```

**Windows (PowerShell, native Codex)**

```powershell
py -3 scripts/setup.py
```

If Python is available as `python`, use it in place of `py -3`. The installer uses `%USERPROFILE%\.codex` or your configured `CODEX_HOME`. If discovery fails, pass `--codex` with the full path to `codex.exe`. [Codex on Windows](https://learn.chatgpt.com/docs/app/windows)

Setup installs the plugin and verifies that Codex can discover it. Add `--coordinator` to the same command to set the optional GPT‑6.1 Sol/`high` default.

Open `/hooks` in Codex CLI and review the Switch Power hooks. Approve the ones you want to enable, then start a new Codex session. The installer registers the plugin for your user profile and adds a managed block to the global `AGENTS.md` or `AGENTS.override.md`. If Codex does not discover the bundled hooks, setup registers them in your profile's `hooks.json`.

## Use

Give Codex a normal request such as “Count the `.py` files in `scripts/`.” When a suitable lightweight executor is available, the coordinator delegates the count and checks the result. Your current chat model receives the next request and chooses the route again.

The coordinator selects the model and reasoning effort of each native subagent. The verified V2 tool schema requires `fork_turns: "none"` for explicit overrides, so the coordinator passes the relevant context, boundaries, and acceptance criteria in the assignment. Codex controls the model of the main chat.

## Model and token usage

Switch Power 0.1.3 emits a one-line Codex hook notice after the answer, for example `Switch Power · gpt-6.1-sol + gpt-6-luna · 31,873 tokens`. In the desktop app, review the new hooks in **Settings → Hooks**. In Codex CLI use `/hooks`. The notice uses Codex’s native warning channel, so its placement depends on the client.

The total includes input (including cached input) and output reported by Codex for the coordinator and attributed workers. If known usage is missing, the notice says `partial` or `token usage unavailable`. See the [live benchmark and reproduction steps](docs/usage-benchmark.md).

On three small file tasks, Switch Power used 7.18× as many raw tokens as standalone Sol/high across six valid pairs.

## Coordinator settings

`configure.py apply` checks the native catalogue before setting Sol/`high` and saves the previous two values. `upgrade` only applies an available Sol upgrade declared by the catalogue that supports `high`. On Windows, use `py -3` in place of `python3` for the commands below.

```bash
python3 scripts/configure.py inspect
python3 scripts/configure.py upgrade
python3 scripts/configure.py restore
```

## Disable or remove

Run the corresponding command in the source or extracted directory. Start a new Codex session after changing the plugin state.

```bash
python3 scripts/install.py disable
python3 scripts/install.py enable
python3 scripts/install.py remove
```

On Windows, use `py -3 scripts/install.py disable`, `enable`, or `remove`. `disable` removes the managed instruction block and Switch Power's fallback hooks. `remove` also uninstalls the plugin and its marketplace. Restore the coordinator default separately with `configure.py restore`.

## Development and verification

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

Version 0.1.2 passed 31 tests and a fresh installation from the archive on macOS. Tests cover Windows hook command formatting. End-to-end testing in native Windows Codex remains open.

Hooks validate the requested model, effort, task scope, and recorded consent for calls they intercept. The coordinator interprets whether a request starts a new task and whether the user's message grants consent. Temporary state includes the latest prompt for matching a consent quote and is cleared on `finish`. A successful spawn shows that Codex accepted the request. Backend model attestation requires separate Codex metadata.

- [Architecture and troubleshooting (Russian)](docs/architecture.md)
- [Verification report (Russian)](docs/verification.md)
- [Requirements](specs/001-global-coordinator/spec.md) · [Implementation plan](specs/001-global-coordinator/plan.md) · [Spec Kit tasks](specs/001-global-coordinator/tasks.md)

[Codex plugins](https://developers.openai.com/plugins/build/plugins) · [Global AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) · [Codex hooks](https://learn.chatgpt.com/docs/hooks) · [GitHub Spec Kit](https://github.com/github/spec-kit)
