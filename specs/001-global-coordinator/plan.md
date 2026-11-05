# Personal coordinator implementation plan

Goal: private global Codex plugin with inspectable routing policy.
Architecture: native skill and subagents; stdlib Python helpers discover models
and validate grants; native hooks guard ordinary launches. Installation and main
model defaults are separate scripts. Spec: [spec.md](spec.md). Date: 2026-11-05.

## Technical Context
Python 3.11+, JSON manifests, Markdown. Private session JSON, file locking and
atomic writes. Catalogue via paginated native `model/list`, with actual spawn
allowlist supplied from its schema. Tests: unittest and temporary directories;
live native plugin install/list, skills/list and hooks/list. No paid API/server.

## Constitution Check
Native-only, consent scope, original chat, preserved settings and honest evidence.
Hook trust is never auto-granted; launch arguments are not backend attestation.

Runtime adaptation: this installed Codex does not discover bundled plugin hooks.
Installer detects this through native hooks/list and registers the same handlers
in supported user hooks.json, preserving unrelated callbacks. Disable removes
those owned callbacks independently of the Python interpreter used to install.

## Decisions and alternatives
Chosen: skill + guardrail hooks + global AGENTS bootstrap. A skill alone does not
guarantee activation every chat. An MCP router cannot own the native parent spawn
tool and adds unnecessary infrastructure. Main model is configured separately.
User authorized reversible choices without a design approval stop.

## Files and interfaces
- `plugins/switch-power/`: manifest, coordinate skill, hooks and Python runtime.
- `scripts/policy.py` inside plugin: catalogue, permission, recommendation, upgrade.
- `scripts/runtime.py` inside plugin: task/scope/grant/check/status and catalogue RPC.
- `hooks/guard.py`: native lifecycle and PreToolUse adapter.
- root `scripts/install.py`: native marketplace install, global bootstrap, disable.
- root `scripts/configure.py`: separate model defaults apply/restore.
- `tests/`: policy, state, catalogue, config preservation, packaging/install.
- root `scripts/build.py`: archive/checksums; `docs/verification.md`: evidence.

## Execution
Inline implementation with independent Sol/high final review. Write meaningful
failing tests before code, implement and verify. Use Spec Kit prerequisite and
template resolution scripts. Keep development integration local.

## Review Focus
Stale grants across tasks; inheritance ignoring model overrides; catalogue versus
spawn allowlist; existing global config/AGENTS overrides; hook trust and bypasses.
