# Manual JANG 3L Long Review

Generated on 2026-04-14 after running the benchmark harness directly against the aux JANG runtime at `http://127.0.0.1:8001`.

This note summarizes the tracked long-run results for:

- `MiniMax-M2.7-JANG_3L`
- full baseline suite (`full`)
- Claude-Code-style prompt suite (`qwen_cc`)

Ignored raw JSON outputs were written to:

- `results/manual-MiniMax-M2.7-JANG_3L-full-summary.json`
- `results/manual-MiniMax-M2.7-JANG_3L-qwen-cc-summary.json`
- `results/manual-MiniMax-M2.7-JANG_3L-long-runs-index.json`

Ignored raw power log was written to:

- `/tmp/powermetrics_jang_3l_long_20260414_142018.log`

## Environment Notes

- Backend under test: aux oMLX / JANG runtime on port `8001`
- API route: `http://127.0.0.1:8001/v1`
- API key: aux local key
- Memory policy during the run: aux max model memory temporarily raised to `96GB`
- Unload discipline was enforced before and after the suite run
- Wrapper and Docker Hermes were stopped during the run to reduce contention
- After the run, aux memory was restored to `16GB` and services were restarted
- Real root-backed `powermetrics` sampling was active during the benchmark window

## Headline Scores

| Suite | Overall score | Notes |
| --- | --- | --- |
| `full` | `57.59` | Very strong instruction compliance, middling chat, better code than 2L, weaker long-context retention than 2L |
| `qwen_cc` | `66.66` | Better than 2L on CC-style stress prompts, especially on code-oriented tasks |

## Full Suite Summary

Dimension scores:

- instruction: `100.0`
- chat: `80.0`
- code: `66.67`
- long_context: `50.0`

Task breakdown:

- total tasks: `22`
- perfect: `13`
- partial: `0`
- zero: `9`
- deferred: `0`
- failed: `0`
- prompt tokens: `50552`
- completion tokens: `7931`

### Full Suite Strengths

Perfect-score tasks:

- `full_text_concise_following`
- `full_text_json_extract`
- `full_text_multi_turn_memory`
- `full_text_verbosity_control`
- `full_text_bilingual_precision`
- `full_text_tradeoff`
- `full_text_instruction_persistence`
- `full_code_sum_even`
- `full_code_bugfix_discount`
- `full_code_tests_author`
- `full_code_cli_format`
- `full_long_instruction_retention`
- `full_long_cross_section`

Interpretation:

- JANG 3L can execute the full suite cleanly end-to-end without the earlier broken-runtime failure mode.
- Instruction-following was materially stronger than 2L on this pass.
- Code scores improved over 2L when the scorer accepted the artifact shape.

### Full Suite Weaknesses

Zero-score tasks:

- `full_text_style_stability`
- `full_code_group_words`
- `full_code_edit_slugify`
- `full_long_retrieve_early_fact`
- `full_long_distractor_resistance`
- `full_tool_status`
- `full_tool_web_docs`
- `full_tool_selection`
- `full_tool_live_search_reference`

Partial-score tasks:

- none

Interpretation:

- The main weakness was not total failure to answer, but brittle behavior under exact long-context retrieval and strict scorer expectations.
- Compared with 2L, 3L traded some long-context reliability for better instruction/code performance.
- MCP stayed unhealthy in aux during this run, so these results reflect non-tool benchmark behavior.

## Qwen-CC Suite Summary

This suite was designed for Qwen-family Claude-Code-style prompting, but was forced onto JANG 3L as a cross-family stress test.

Dimension scores:

- instruction: `100.0`
- chat: `100.0`
- code: `33.33`
- long_context: `100.0`

Task breakdown:

- total tasks: `6`
- perfect: `4`
- partial: `0`
- zero: `2`
- failed: `0`
- prompt tokens: `764`
- completion tokens: `1291`

### Qwen-CC Strengths

Perfect-score tasks:

- `qcc_instruction_edit_plan`
- `qcc_chat_review_risk`
- `qcc_code_fix_notify_user`
- `qcc_long_repo_constraint`

Interpretation:

- JANG 3L was notably better than JANG 2L on this suite overall.
- It remained strong on terse planning/review prompts and improved on code-oriented CC-style tasks.
- This makes 3L the more credible Claude-Code-style stress candidate of the two JANG variants tested so far.

### Qwen-CC Weaknesses

Zero-score tasks:

- `qcc_code_slugify_file`
- `qcc_code_bugfix_discount`

Partial-score tasks:

- none

Interpretation:

- The remaining misses were still concentrated in strict code artifact compliance.
- Even when 3L understood the task, it could still leak reasoning or over-explain instead of emitting only the demanded patch/file shape.

## Real Power Summary During Benchmark Window

The benchmark window covered approximately `14:20:33` to `14:35:29` local time with `powermetrics` running throughout.

Samples captured inside the benchmark window: `776`

Power statistics:

- CPU power average: `4798.58 mW`
- CPU power median: `5075.0 mW`
- CPU power peak: `10754 mW`
- GPU power average: `22161.74 mW`
- GPU power median: `21600.5 mW`
- GPU power peak: `53308 mW`
- Combined power average: `26960.34 mW`
- Combined power median: `27282.0 mW`
- Combined power peak: `54063 mW`

Interpretation:

- This 3L long-run pass was primarily GPU-power dominated on the M5 Max machine.
- Combined package power averaged roughly `26.96W` during the measured benchmark window.
- Median combined power stayed near `27.28W`, with a short peak just above `54W`.

## Comparison to JANG 2L

Headline comparison:

- `full`: 2L scored `57.69`, 3L scored `57.59` → effectively tied
- `qwen_cc`: 2L scored `61.11`, 3L scored `66.66` → 3L clearly improved

Practical interpretation:

- 3L is not a universal upgrade over 2L on every dimension.
- For the full suite, 3L bought stronger instruction/code behavior but gave back long-context strength.
- For the Claude-Code-style stress suite, 3L was the stronger JANG variant.

## Behavioral Takeaway

The most important result is that JANG 3L is now stable enough to complete longer benchmark suites on the aux runtime while being measured with real power sampling.

Practical behavior from this pass:

- stronger than 2L on instruction-heavy and CC-style code stress prompts
- still vulnerable to exact output-shape failures on brittle code tasks
- not clearly better than 2L on long-context retrieval
- a better candidate than 2L when the use case looks like terse planning/review plus moderate code synthesis

## Recommendation

For future JANG testing:

- keep both `MiniMax-M2.7-JANG_2L` and `MiniMax-M2.7-JANG_3L` in the pool, because they fail differently
- prefer `3L` for Claude-Code-style or code-adjacent stress prompts
- keep `2L` as the cheaper/leaner option when long-context retention matters more than raw CC-style code score
- continue measuring with real `powermetrics` when comparing JANG variants, because 3L can now be evaluated on quality and power at the same time
