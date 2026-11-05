# Research

Official github/spec-kit commit ec9a6f3b94c0aa856f77e550785a1ddde1993de1,
CLI 1.3.1.dev0, locally installed with Codex skills and events disabled. Development
cryptography pinned to compatible binary 48.0.1 after installed Rust rejected the
newest source build. Runtime has no external dependencies.

Codex 0.166.0-alpha.6 generated actual JSON schemas. Live model/list returns ten
models; actual current spawn schema exposes five. All upgrade metadata is null.
Actual spawn overrides require fork_turns none, despite a stale skill reference.
Native Sol/high research child successfully returned a normal final result.
No message-to-parent route. Backend model is not independently attested.

Sources:
- [Plugins](https://developers.openai.com/plugins/build/plugins): root manifest,
  private local marketplace, personal enabled state and installed cache.
- [Hooks](https://learn.chatgpt.com/docs/hooks): trust required; ordinary spawn_agent
  alias Agent and code-mode calls supported; specialized paths may opt out;
  errors/timeouts can fail open in host. This is a guardrail, not a security boundary.
- [AGENTS](https://learn.chatgpt.com/docs/agent-configuration/agents-md): global
  CODEX_HOME instruction, override precedence, read once per run.
- [Models](https://learn.chatgpt.com/docs/models) and
  [selection](https://developers.openai.com/api/docs/guides/model-selection):
  initial roles are useful priors, not account-specific launch capabilities.
