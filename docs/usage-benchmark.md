# Switch Power token usage

Switch Power uses the native Codex `PostModelRequest` and `Stop` hooks. It emits a single notice after the answer with the model IDs reported by Codex and the total observed tokens for that turn. The notice uses Codex's warning channel. Its presentation depends on the client. Review the hooks in Codex settings or via `/hooks` in the CLI after installing the update. The notice needs a Codex build that supports `PostModelRequest`.

The total includes the coordinator and workers whose native lifecycle events associate them with the turn. It includes cached input and output. Reasoning tokens are already part of output. Missing usage and known gaps in worker coverage are labelled `partial` or `token usage unavailable`. The hook does not make an extra model request. The usage state is local and contains no prompts or answers. It keeps current counters and recent worker identifiers to avoid attributing late events to the next turn. Model IDs in the notice come from the host's attempt events.

The native App Server smoke test used Codex CLI `0.166.0-alpha.6` on macOS. It received the final answer and then a hook warning of `Switch Power · gpt-6.1-sol · 31,873 tokens`, matching the native turn total. A second smoke test returned 437 before the notice `Switch Power · gpt-6.1-sol + gpt-6-luna · 187,235 tokens`. The native counters reported 171,125 for Sol and 16,110 for Luna. The desktop client's placement was not inspected. On this build, non-interactive `codex exec --json` did not include the hook notice in its JSON stream.

## Repeat the live benchmark

Run from the project root with a signed-in Codex profile. The benchmark uses normal Codex quota and accepts an explicit `--auth-file` when the default file is unavailable. The benchmark compares two isolated profiles and does not change your primary Codex settings.

```sh
python3 scripts/benchmark_usage.py --repeats 2 --output usage-benchmark.jsonl
```

It runs three deterministic file tasks in fresh ephemeral Codex sessions, with two paired repetitions per task. Each run uses GPT-6.1 Sol at high in the main session, the same synthetic project and workspace-write sandbox. The baseline disables native subagent features and instructs the coordinator to work alone. A control is rejected if native workers are still observed. The plugin profile enables the native V2 agent tool and loads Switch Power through the real installer. The default command reverses the order for the second repetition. Both profiles use the same measurement hooks, which record numeric usage and native model and worker identifiers. We check the final answer, compare the coordinator event totals with the CLI's total, and require start, usage and stop events for each worker. Cached counts are recorded separately. Raw token totals are not a measure of credits or subscription quota.

## Version 0.1.4 measurements

Fresh runs on the same three prompts and fixture used Codex CLI `0.166.0-alpha.6` on macOS on November 5, 2026. All 12 runs returned the expected answer and passed the usage checks. Both arms recorded zero workers on these tasks. An additional test with an explicit Luna/low request returned the correct port and completed one native Luna worker. That test is separate from the comparison.

| Task | Sol/high alone, tokens | Switch Power 0.1.4, tokens | Plugin change | Solo median time | Plugin median time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Look up one port in TOML | 59,878 | 65,744 | +9.8% | 10.10 s | 10.77 s |
| Count Python files | 64,611 | 70,462 | +9.1% | 10.47 s | 12.17 s |
| Sum pending amounts in two CSVs | 153,496 | 111,233 | -27.5% | 22.66 s | 20.70 s |
| All six pairs | 277,985 | 247,439 | -11.0% | 11.46 s | 12.26 s |

Switch Power 0.1.4 used **11.0% fewer raw tokens** than fresh standalone Sol/high runs, and **87.4% fewer** than version 0.1.3 on the same suite. The TOML and file count tasks used more tokens with 0.1.4. The savings in the combined sample came from the CSV task. The baseline counted 208,640 cached input tokens, and the plugin counted 164,096. The small sample does not establish a general savings rate.

[Per-run evidence for 0.1.4](evidence/usage-benchmark-0.1.4.jsonl).

## Version 0.1.3 measurements

Codex CLI `0.166.0-alpha.6`, macOS, November 5, 2026. All 12 included runs returned the expected answer and passed the usage coverage checks. Every included baseline ran on GPT-6.1 Sol/high alone. Every plugin run used Sol/high and one or two native Luna workers.

| Task | Sol/high alone, tokens | Switch Power, tokens | Plugin / baseline | Solo median time | Plugin median time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Look up one port in TOML | 63,349 | 485,833 | 7.67× | 10.95 s | 48.41 s |
| Count Python files | 88,201 | 661,279 | 7.50× | 15.19 s | 57.09 s |
| Sum pending amounts in two CSVs | 121,011 | 810,860 | 6.70× | 19.12 s | 61.67 s |
| All six pairs | 272,561 | 1,957,972 | 7.18× | 13.20 s | 57.09 s |

The plugin used **7.18× as many raw tokens** as standalone Sol/high on this suite, an increase of **618.4%**. Sol accounted for 1,523,848 of the plugin's 1,957,972 tokens. The plugin counted 1,675,520 cached input tokens and the baseline counted 227,328. Timing includes startup and is descriptive, since collection of some control and plugin runs overlapped.

The included controls for lookup and inventory had no workers even without the explicit solo instruction. The CSV controls originally delegated despite the feature flags, so they were replaced by controls with an explicit solo instruction. The second plugin inventory run had incomplete telemetry and was repeated once. The tasks are deliberately small and these results measure this suite only.

[Per-run evidence](evidence/usage-benchmark-0.1.3.jsonl) includes separate input, cached input, output, and reasoning totals by model.
