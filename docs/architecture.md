# Switch Power architecture

The coordinator receives each request in the main chat. When delegating, it checks the current model catalogue against the available spawn tool schema. It selects the executor and reasoning effort, defines the scope, verifies consent, and uses the native spawn tool. The coordinator reviews the result and replies in the original chat.

| Component | Purpose |
| --- | --- |
| [`skills/coordinate`](../plugins/switch-power/skills/coordinate/SKILL.md) | Executor selection, coordination, and result review. |
| [`scripts/policy.py`](../plugins/switch-power/scripts/policy.py) | Model availability, consent, and scope checks. |
| [`scripts/runtime.py`](../plugins/switch-power/scripts/runtime.py) | Native catalogue, local task state, and verification CLI. |
| [`hooks/guard.py`](../plugins/switch-power/hooks/guard.py) | Codex lifecycle events and launch checks via `PreToolUse`. |
| [`scripts/install.py`](../scripts/install.py) | Global installation, disabling, and removal. |
| [`scripts/configure.py`](../scripts/configure.py) | Configure or restore the main chat model. |

## Task lifecycle

1. The coordinator handles short local work directly. Before delegating, it weighs the gain against setup, worker time, and verification. An explicit request for a worker still uses the normal consent checks.
2. For delegation, the CLI registers the task and worker scope. The native call specifies the model and reasoning effort when the Codex schema supports them.
3. Astra and efforts above `high` require consent for the exact model, effort, and work scope. Consent is valid for the current task. An independent task starts a new cycle.
4. The coordinator gets the worker result through the native lifecycle, checks it, and replies. The `finish` command clears task state.

Codex configuration sets the main model. Native subagent parameters select the executor for specific work. The main chat receives and reassesses the next request.

With the verified Codex V2 schema, explicit model and effort use `fork_turns: "none"`. The coordinator puts the required context, constraints, and acceptance criteria in the assignment.

## Catalogue and state

The installer obtains the catalogue through `model/list`. The CLI refreshes expired data while preparing delegation and checks age and compatibility with the current spawn schema.

Task state lives in a private user temporary directory. It records scope and the latest request to bind consent. The model catalogue lives separately in the Codex profile. [Runtime command reference](../plugins/switch-power/skills/coordinate/references/runtime.md).

## Troubleshooting

Run `python3 scripts/verify_native.py` from the clone or extracted archive. On Windows use `py -3 scripts/verify_native.py`. The command checks skill discovery and hook state in two directories. If a required hook is `untrusted`, inspect its definition via `/hooks` in Codex CLI. When a native launch fails, the coordinator reports the reason and chooses an available route.

Hook coverage depends on the Codex tool path. The coordinator interprets task boundaries and user consent. [Verification report](verification.md).
