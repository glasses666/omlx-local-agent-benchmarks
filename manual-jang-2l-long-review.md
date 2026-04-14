# Manual JANG 2L Long Review

Generated on 2026-04-14 after running the benchmark harness directly against the aux JANG runtime at `http://127.0.0.1:8001`.

This note summarizes the tracked long-run results for:

- `MiniMax-M2.7-JANG_2L`
- full baseline suite (`full`)
- Claude-Code-style prompt suite (`qwen_cc`)

Ignored raw JSON outputs were written to:

- `results/manual-MiniMax-M2.7-JANG_2L-full-summary.json`
- `results/manual-MiniMax-M2.7-JANG_2L-qwen-cc-summary.json`
- `results/manual-MiniMax-M2.7-JANG_2L-long-runs-index.json`

## Environment Notes

- Backend under test: aux oMLX / JANG runtime on port `8001`
- API route: `http://127.0.0.1:8001/v1`
- API key: aux local key
- Memory policy during the run: aux max model memory temporarily raised to `72GB`
- Unload discipline was enforced before and after the suite run
- Wrapper and Docker Hermes were stopped during the run to reduce contention
- After the run, aux memory was restored to `16GB` and services were restarted

## Headline Scores

| Suite | Overall score | Notes |
| --- | --- | --- |
| `full` | `57.69` | Stronger on instruction/chat/long-context than on strict code-output discipline |
| `qwen_cc` | `61.11` | Surprisingly solid on CC-style planning/review prompts, still weak on strict code artifact delivery |

## Full Suite Summary

Dimension scores:

- instruction: `66.67`
- chat: `86.67`
- code: `58.33`
- long_context: `75.0`

Task breakdown:

- total tasks: `22`
- perfect: `12`
- partial: `2`
- zero: `4`
- deferred: `4`
- failed: `0`

### Full Suite Strengths

Perfect-score tasks:

- `full_text_concise_following`
- `full_text_multi_turn_memory`
- `full_text_style_stability`
- `full_text_verbosity_control`
- `full_text_tradeoff`
- `full_text_instruction_persistence`
- `full_code_sum_even`
- `full_code_tests_author`
- `full_code_cli_format`
- `full_long_instruction_retention`
- `full_long_cross_section`
- `full_long_distractor_resistance`

Interpretation:

- JANG 2L is not weak on long prompts in general.
- It tracks style and memory constraints well when the requested output format is not overly brittle.
- It can still solve small code-generation tasks cleanly when the scorer accepts the response shape.

### Full Suite Weaknesses

Zero-score tasks:

- `full_text_json_extract`
- `full_code_group_words`
- `full_code_edit_slugify`
- `full_long_retrieve_early_fact`

Partial-score tasks:

- `full_text_bilingual_precision` → `33.33`
- `full_code_bugfix_discount` → `50.0`

Deferred tool tasks:

- `full_tool_status`
- `full_tool_web_docs`
- `full_tool_selection`
- `full_tool_live_search_reference`

Interpretation:

- The biggest recurring weakness is strict output discipline, not total task misunderstanding.
- The JSON task showed a format-compliance problem rather than a knowledge failure.
- Code tasks that require a very narrow accepted artifact shape still drag the model down.
- Tool tasks were deferred because MCP remained unhealthy in the aux runtime during this benchmark pass.

## Qwen-CC Suite Summary

This suite was designed for Qwen-family Claude-Code-style prompting, but was forced onto JANG 2L as a cross-family stress test.

Dimension scores:

- instruction: `100.0`
- chat: `100.0`
- code: `22.22`
- long_context: `100.0`

Task breakdown:

- total tasks: `6`
- perfect: `3`
- partial: `1`
- zero: `2`
- failed: `0`

### Qwen-CC Strengths

Perfect-score tasks:

- `qcc_instruction_edit_plan`
- `qcc_chat_review_risk`
- `qcc_long_repo_constraint`

Interpretation:

- JANG 2L is unexpectedly competent at terse planning prompts.
- It can identify regression risk clearly and concisely.
- It retains repo-rule tokens well under CC-style context packing.

### Qwen-CC Weaknesses

Zero-score tasks:

- `qcc_code_slugify_file`
- `qcc_code_bugfix_discount`

Partial-score task:

- `qcc_code_fix_notify_user` → `66.67`

Interpretation:

- The model often understands the repair but still misses the exact scorer contract.
- It tends to mix explanation with code or choose the wrong semantics for percentage / edge-case handling.
- In other words: good planner/reviewer, middling strict patch emitter.

## Behavioral Takeaway

The most important result is that JANG 2L is now stable enough to complete longer benchmark suites without the earlier 500-error failure mode.

Practical behavior from this pass:

- better at instruction-following and long-context retention than the old screening failure suggested
- good at planning and lightweight review prompts
- still unreliable on strict code-output formatting and exact scorer-shape compliance
- likely more useful as a supervised analysis / scouting model than as a final artifact-only coding model

## Recommendation

For future JANG testing:

- keep `MiniMax-M2.7-JANG_2L` in the comparison pool for long-context and planning-oriented evaluation
- do not assume its lower code score means weak reasoning; much of the loss comes from output-shape mismatch
- if the goal is repo-edit automation, pair it with a stronger closer model or a post-processor that strips reasoning / fences and normalizes outputs
