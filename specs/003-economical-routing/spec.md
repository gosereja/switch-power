# Economical routing for routine requests

- FR-001. Complete straightforward local work directly when its expected cost is lower than starting a worker. Examples include a configuration lookup, recursive file count, and independent calculations over two small files.
- FR-002. Consider delegation only for a concrete expected gain after accounting for setup, brief, worker work, coordination and verification. A lower worker tier by itself is insufficient. Preserve explicit delegation requests and existing model and consent checks.
- FR-003. Keep normal direct turns on the configured main model without loading delegation instructions or refreshing the worker catalogue. Preserve native turn capture and usage notices.
- FR-004. Repeat the identical three tasks twice with the updated plugin and with standalone Sol/high. Record correctness, usage coverage and whether a worker ran. Retain previous results for comparison.

Acceptance requires correct answers and complete counters for the paired comparison. An automatic worker on a fixture is a routing regression even if its answer is correct.
