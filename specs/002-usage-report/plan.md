# Implementation plan

Use Codex PostModelRequest to collect counters and the Stop hook to show a system notice after the response. This uses the native warning channel and avoids asking the model to generate the footer. Use native subagent lifecycle signals to associate workers with the root turn. Keep the usage data independent of the consent state and use the existing private locking mechanism. Fall back to a partial notice when the native events do not establish coverage.

Verify the event order and fields with the installed Codex version before implementing. Use ephemeral Codex CLI runs on one fixture and two isolated profiles with the same account, root model, reasoning effort, sandbox and approval policy. Enable native V2 agents in the plugin profile and disable delegation in the standalone baseline. Alternate modes, validate answers, and record measured tokens for each valid run. Document both results and client rendering limits.
