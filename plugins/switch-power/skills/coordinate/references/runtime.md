# Runtime CLI and platform boundaries

Use Python 3.11+ on macOS, Linux and Windows. In Windows PowerShell use `py -3`
or the installed `python` instead of `python3`. Resolve the installed plugin root from this skill
location, two levels above `skills/coordinate/`. Scripts live at `scripts/runtime.py`.
Use proper shell quoting for task descriptions and user quotes; prefer structured
subprocess arguments for arbitrary text. Do not interpolate user text into shell.

All commands run locally. They never spawn an agent. Default session comes from
`CODEX_THREAD_ID`; otherwise pass the native root session ID with `--session`.
`UserPromptSubmit` context also reports that ID and the captured turn ID.

```text
python3 <plugin-root>/scripts/runtime.py --session ROOT_ID catalog
  --spawn-model EXACT_ID [--spawn-model OTHER_EXACT_ID ...]
  --spawn-effort low --spawn-effort medium --spawn-effort high [...]
```

Supply values from the **actual current spawn schema**, never a hardcoded list
from this document. Installation seeds a fresh profile catalogue via native
`model/list`. The `catalog` command uses a fresh snapshot or refreshes it from
Codex when delegation needs it, then intersects it with the launch schema per
session. Routine prompts do not refresh the catalogue. An expired catalogue is
never used to launch.

```text
runtime.py --session ROOT_ID task --new --description "Independent objective"
runtime.py --session ROOT_ID task --continue
runtime.py --session ROOT_ID scope --id review --description "Read-only review of the implementation"
runtime.py --session ROOT_ID status
```

Use the returned `task_name`, e.g. `sp_<random-task-id>__review`, verbatim in spawn.
Scope IDs are ASCII lowercase letters, digits and underscores, max 48. Scope
descriptions cannot be changed; this prevents reusing permission for expanded work.

```text
runtime.py --session ROOT_ID propose --model EXACT_ID --effort high
  --scope review --reason "Concrete quality benefit for this review"
runtime.py --session ROOT_ID grant --model EXACT_ID --effort xhigh
  --scope review --source live_user --turn-id CURRENT_TURN
  --quote "Verbatim explicit permission in the current captured user prompt"
runtime.py --session ROOT_ID check --model EXACT_ID --effort medium
  --task-name RETURNED_TASK_NAME --fork-turns none
runtime.py --session ROOT_ID failed --model EXACT_ID --effort medium
  --scope review --reason "Native launch error or failed executor result"
runtime.py --session ROOT_ID finish
```

Short yes/да requires an exact earlier pending proposal and a later captured
user turn. Direct consent requires no proposal. Only the coordinator records
consent; child agents may check the inherited task, but never grant or redefine it.
If hooks are not trusted and no real prompt was captured, restricted permission
cannot be recorded through this helper. Explain the trust/setup limit; do not
fabricate a prompt event. Safe work can continue in the main chat.

`recommend --kind narrow|visual|code|analysis --complexity 0..4 --ambiguity 0..4
--priority balanced|quality|speed|limits` ranks **all** compatible catalogue entries.
This is an optional aid, not an automatic cost decision or a live execution test.

State is private local JSON below `/tmp/switch-power-<uid>-<profile-hash>` on
Unix or `%LOCALAPPDATA%\Temp\switch-power-<profile-hash>` on Windows, with
locking and atomic replacement. Hook and CLI use the same profile-scoped path. It contains
the latest user prompt to bind consent evidence, plus hashes of quoted grants.
`finish` clears the session state. Disabling retains it for inspection; the user
can remove that owned state directory after closing active sessions.

## What is and is not enforced

Ordinary PreToolUse launch checks verify catalogue age, availability, supported
effort, explicit fork, root task, registered scope and exact permission grant.
SubagentStart injects recursive rules; it cannot block an already starting agent.

Semantic classification of “new independent task”, “same-task steering”, “live
explicit user request” and “document quotation” remains the coordinator's duty.
The CLI records that classification and verifies the captured quote; it cannot
independently prove its meaning. Scripts/state are user-editable. Hooks require
trust, may fail open in the host, and specialized tools can opt out. This is a
testable guardrail plus instructions, not a tamper-proof authorization system.

Global AGENTS is loaded for new runs, subject to precedence and byte limits.
Remote/cloud orchestration and managed installs may not load these local hooks.
Use native capability errors as evidence; never switch to UI automation/API
workers or create user chats as a workaround.
