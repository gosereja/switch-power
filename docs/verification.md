# Switch Power verification

## Versions 0.1.3 and 0.1.4

Version 0.1.3 added the token notice. A live Codex App Server confirmed the totals for both direct and delegated answers. Version 0.1.4 handles short tasks directly unless delegation is worthwhile. It passed 38 tests and an upgrade from the archive in an isolated profile. All 12 reruns returned the correct answers with complete counters. A separate explicit request successfully launched Luna/low. [Method and results](usage-benchmark.md).

## Version 0.1.2

Added PowerShell installation with native `codex.exe`, Windows state locks, cross-platform App Server pipes, and Windows hook commands that handle spaces and apostrophes in paths. On macOS, 31 tests passed. We also verified one-command installation from the archive in a clean profile, Sol/high configuration, and skill discovery from two directories. Windows command generation passed tests. A full native Windows run remains open.

## Version 0.1.1

Each request was evaluated afresh. This version preferred a lightweight worker for simple delegated work while Sol/high coordinated and checked the answer in the original chat. The sandbox denied state writes under `~/.codex` and the child App Server failed to initialize SQLite. The fix moved state to a private temporary directory and reused a fresh model catalogue. The personal profile discovered the upgrade and four trusted hooks in two directories.

Twenty-nine tests passed. The sandbox exposed a catalogue of ten models. We registered a scope, authorized Luna/low, and Codex accepted the native launch. The worker returned five Python files in `scripts/`, matching an independent count. The behavior on a second turn and backend attestation were still open at this stage.

## Initial verification of version 0.1.0

The tests ran on November 5, 2026 (Europe/Podgorica), with Codex CLI 0.166.0-alpha.6 from the installed desktop app.

- Integrated official GitHub Spec Kit 1.3.1.dev0 at commit `ec9a6f3b94c0aa856f77e550785a1ddde1993de1`. Created the constitution, spec, plan, research, data model, contracts, and tasks. The native prerequisite check passed.
- Generated App Server schemas and inspected the actual spawn tool. Native `model/list` returned ten models without opening a user chat, including gpt-reserve, older 5.6 variants, and codex-auto-review. The spawn schema admitted five models. Launch eligibility uses the intersection.
- A native Sol/high worker accepted a read-only research task and returned a final result. The request specified model and effort. Backend attestation was unavailable.
- Native marketplace and plugin installation succeeded in an isolated `CODEX_HOME`. Skill discovery returned `switch-power:coordinate` as an enabled user skill in two unrelated directories.
- The tested Codex build did not discover bundled hooks, including through the compatibility manifest. The user `hooks.json` fallback discovered four hooks in both directories with no loader errors. They were untrusted. The installer checks this fallback automatically.
- Twenty-seven tests covered local policy, CLI and hook JSON, state, locks, installation, preservation of other settings, direct consent, exact scope and model/effort, restricted launches, stale or unavailable models, stale-prompt replay, worker failure, invalid state, and incomplete prompt events.
- Verified installation from the archive, disable → enable → remove, and discovery again in an isolated profile. Disabling or removing removed the skill, its hooks, and the managed AGENTS block. Two builds of the same source produced identical ZIPs. Internal `SHA256SUMS` matched.
- The isolated profile verified apply → inspect → upgrade (no-op) → config/read → restore for the main model. Codex confirmed gpt-6.1-sol/high. The personal profile was untouched during this test.
- A Sol/high review found two defects in multiline TOML and disabling after changing Python. Failing tests reproduced both defects, which were fixed. A second review covered 27 tests, additional TOML cases, apply/restore, and install/reinstall/disable, with no further findings.
- A native Luna/medium worker read the skill and gave the expected decisions in ten scenarios covering simple and visual work, Astra without consent, explicit Astra/xhigh, independent tasks, README instructions, approval of a proposal, an incompatible catalogue, backend self-report, and missing launch parameters. This was one behavioral check.

[Enabled discovery](evidence/native-enabled.json) · [Disabled discovery](evidence/native-disabled.json) · [Coordinator configuration](evidence/coordinator-config.json) · [Model catalogue](evidence/catalogue.json). The checks used diagnostic App Server connections and created no user-owned chats.

## Spec Kit consistency

The spec, plan, tasks, constitution, and source paths were checked. Tasks covered 14 of 14 requirements, with zero constitution conflicts and zero unfinished placeholders. Task coverage and live verification are tracked separately.

| Requirement | Tasks | Main evidence |
| --- | --- | --- |
| FR-001 | T005, T007, T009 | Global bootstrap and native discovery across directories |
| FR-002 | T001, T004, T005 | Model, effort and fork checks plus live Sol and Luna runs |
| FR-003 | T001, T004, T008 | Native catalogue and intersection with spawn schema |
| FR-004 | T003, T004 | Tests for preauthorized model families and efforts |
| FR-005 | T003, T004, T005 | Denial and consent tests. Live interception open at this stage |
| FR-006 | T003, T004, T005 | Scope, direct consent and proposal tests |
| FR-007 | T003, T004, T005 | Reset, replay and evidence-source checks |
| FR-008 | T004, T005 | Task, scope and `SubagentStart` rules. Recursive live path open |
| FR-009 | T003, T004, T005 | Unavailable and failed launches, bounded recovery |
| FR-010 | T006, T007 | Native configuration read and restore |
| FR-011 | T004, T008 | Upgrade metadata tests and live no-op |
| FR-012 | T007, T009 | Native install, discovery, disable, enable and remove |
| FR-013 | T009, T010 | Executable tests, archive checks and verification limits |
| FR-014 | T001, T002, T010 | Official local integration and consistency review |

## Limits of live verification

- No Astra or effort above `high` was run for development. Local policy and hook executions covered those cases with controlled inputs.
- At the 0.1.0 stage, the initial audit did not verify live interception after user trust, recursive interception, or namespaced tool names in live payloads. The later live checks are described above and in the benchmark.
- Skill discovery and the managed AGENTS block were verified without creating user-owned chats. Desktop rendering and behavior across successive turns require verification in the target client.
- Spawn responses and worker self-reports are insufficient to attest backend model or effort. The coordinator interprets independent tasks and consent. A quote and `source=live_user` associate evidence with a turn.
- The tested catalogue provided no Sol `upgrade` or `upgradeInfo` metadata, so the native test verified the safe no-op.
- Native Windows, remote/cloud orchestration, managed workspace policy, and specialized tool paths remain outside the verified scope. Hooks provide a guardrail with coverage that varies by runtime.
