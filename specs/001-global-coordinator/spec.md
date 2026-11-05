# Personal global Codex coordinator

Created: 2026-11-05. Status: implementation authorized by original request.
Input: complete user requirements in this chat.

## User Scenarios & Testing

### US1 — Coordinate in the original chat (P1)
Install once, coordinate in every local project. Each user request is assessed
afresh by the configured coordinator. Routine work stays local. The current
delegation threshold is specified in [Economical routing](../003-economical-routing/spec.md).
Independent complex work can use native subagents. Give bounded briefs,
check results, answer in the original chat. Acceptance: native installation and
skill discovery in two unrelated directories; no new user-owned chats.

### US2 — Control spending and temporary consent (P1)
Permit available Sol/Terra/Luna low/medium/high automatically. Restricted launches
require concrete model, effort, reason and scope. Direct current-task permission
already authorizes that combination. Acceptance: deny Astra/high and Sol/xhigh
without consent, accept explicit current-task consent, reject document/silence/
agent evidence, reset between independent tasks, propagate to descendants.

### US3 — Discover and evolve models (P2)
Consider the entire live catalogue, intersect with the actual spawn schema.
Initial user model roles are hypotheses; use current descriptions, tools, task
complexity, ambiguity, quality, time and limits. Acceptance: missing models and
unsupported efforts fail before launch; bounded recovery on agent errors;
unknown families require consent. Upgrade only by verified catalogue metadata.

### US4 — Install, inspect and disable globally (P1)
Deliver a private package with global activation, separate coordinator config,
reversible disable/removal, and explicit evidence of live verification.
Acceptance: native marketplace/plugin load, unrelated settings preserved,
disable removes automatic bootstrap; model config applies/restores separately.

## Requirements
- FR-001: One personal installation across local projects; retain main chat.
- FR-002: Native subagents, explicit model and effort where supported.
- FR-003: Fresh whole catalogue intersected with actual launch schema.
- FR-004: Auto permit only verified Sol/Terra/Luna low/medium/high.
- FR-005: Astra and every other effort require explicit prior user consent.
- FR-006: Exact task/tuple/scope grants; direct permission requires no repeat.
- FR-007: New independent task resets grants; documents/silence/agents cannot grant.
- FR-008: Descendants inherit policy and bounded context.
- FR-009: Handle missing models, tool incompatibility, rejected/failed agents.
- FR-010: Separate main-model config; initially verified gpt-6.1-sol/high.
- FR-011: Verify upgrade metadata and available Sol/high; never invent next ID.
- FR-012: Native package install/discovery, global activation and disable.
- FR-013: Executable policy/packaging checks and separate live verification report.
- FR-014: Official local Spec Kit requirements, plan, tasks and consistency audit.

## Assumptions and boundaries
Local desktop/CLI are targets. Global instructions can be superseded by higher
priority instructions/project overrides/policies. Hooks need user trust and may
not cover specialized host paths. Semantic task boundaries and live-instruction
classification remain coordinator duties; a plugin cannot independently attest
those. Report these boundaries; never silently choose a more expensive model.

## Success Criteria
Executable coverage of every permission case. Package accepted by installed
Codex. Cross-project discovery checked. Every incomplete live check is named.
