# Turn usage and measured comparison

## Requirements

- FR-001. Show a one-line Switch Power notice after a local Codex response. Use the model identifiers and token counts reported by Codex for that turn.
- FR-002. Include native workers when attributable to the turn. Label incomplete counts when a request lacks usage or worker coverage cannot be verified. Separate input, cached input and output in machine-readable evidence. Reasoning is a breakdown of output.
- FR-003. Keep collection local, record counters and model identifiers only, avoid reading the transcript, and leave authorization state independent of usage.
- FR-004. Benchmark identical read-only tasks with and without Switch Power, each starting on GPT-6.1 Sol/high. Validate identical expected output, count all attributable model requests, report elapsed time, and publish the measurements and method in the repository.
- FR-005. Document how to see the line, what it measures and how to interpret the measured difference. Preserve the existing installation platforms and hook trust flow.

## Acceptance

A verified direct turn emits the model and total. A delegated turn either includes native worker usage or labels the gap. Two turns in one session cannot mix. A benchmark with missing usage or an incorrect result cannot be presented as a complete comparison.
