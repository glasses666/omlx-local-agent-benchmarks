# Manual Screening Review

Generated from [`screening-summary.json`](/Users/dracoglasser/自定程式/codex_playground/2026-04-08-1943-cinder-benchmark/results/screening-summary.json) after reading raw model outputs. This review treats the automatic scores as a coarse filter only.

## Scoring Biases Observed

- A large share of low scores are formatting failures rather than understanding failures.
- The most common failure mode is reasoning leakage: `Thinking Process`, `<think>`, or `<analysis>` text appears ahead of an otherwise usable answer.
- JSON tasks are under-scored for models that wrapped correct JSON in fenced code blocks.
- Code-edit tasks are under-scored for models that produced logically correct code but included `import re`, long prefacing text, or both.
- Tool-use remains deferred for every model because MCP is still unhealthy until oMLX is restarted against the converted JSON config.
- One Huihui variant was not benchmarkable in practice because it returned server-side 500 errors across nearly every task.

## Revised Shortlist By Use Case

- Main writing/chat: `gemma-4-26b-a4b-it-4bit`, `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`
- Coding with supervision: `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`, `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-4bit`, `MLX-Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-8bit`
- Vision-first: `gemma-4-26b-a4b-it-4bit`, `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`, `Qwen3.5-35B-A3B-4bit`
- Lightweight local fallback: `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`
- Exclude from deeper testing unless you specifically want to debug them: `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`, `Qwen3.5-9B-mlx-vlm-mxfp4`

## Model Notes

### `gemma-4-26b-a4b-it-4bit`

- Human read: best all-rounder in the current screening set.
- Writing quality is clean and direct. It followed the 12-word constraint correctly, recalled memory correctly, and handled both long-context tasks cleanly.
- JSON extraction was semantically correct and only lost automatic credit because it used fenced JSON.
- Code output quality is solid. The `slugify` edit appears logically correct; the automatic scorer is too strict here.
- Vision answers are concise and grounded.
- Recommended role: first-choice baseline candidate for chat, general writing, and vision.

### `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`

- Human read: stronger writer than coder.
- It produced the cleanest JSON output of the text-only models and handled memory and long-context tasks well.
- The concise-writing miss was mild: the answer was sensible, just not exactly on the requested word count.
- Code tasks are dragged down by `<think>` leakage and verbosity, not by obvious reasoning weakness.
- Recommended role: include as a writing-focused baseline finalist even if the automatic score underrates its practical writing value.

### `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`

- Human read: better than the raw score suggests.
- Text tasks lost points mostly because it added wrappers such as fenced JSON or explanatory phrasing around a correct answer.
- The code-edit sample is logically correct and practical.
- Long-context and vision outputs were both strong and concise enough to be useful.
- Recommended role: strong lightweight candidate for coding plus vision, and worth full baseline despite low automatic text scores.

### `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-4bit`

- Human read: capable, but noisy.
- It solved several code and retrieval tasks correctly, but it leaks full reasoning traces on strict-format prompts.
- This model looks more useful for supervised coding or analysis than for polished end-user chat.
- Vision smoke failed with a server 500, so I would not trust it as a stable VLM yet.
- Recommended role: keep for code-oriented baseline testing, not as a primary writing model.

### `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`

- Human read: unstable, not just weak.
- It returned 500 errors across nearly every task, so the low score is a stability problem, not an evaluation nuance.
- Recommended role: drop from deeper benchmark passes unless your goal is to debug this exact model/backend combination.

### `Huihui-Qwen3.5-27B-Claude-4.6-Opus-abliterated-mlx-8bit`

- Human read: mixed.
- It can answer memory, long retrieval, and vision tasks, but strict formatting is weak and it often exposes analysis text.
- It is less reliable than `gemma` or the better Qwen variants for polished outputs.
- Recommended role: secondary vision candidate only if you want another Huihui comparison point.

### `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

- Human read: reasoning-heavy, output-discipline-light.
- It often understands the task, but emits planning text before the answer.
- Long-context retrieval was semantically correct in at least one case, but it still lost score by not obeying the “exact code only” format.
- Recommended role: maybe useful for supervised analysis, but not a top candidate for polished writing or direct code insertion.

### `MLX-Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-8bit`

- Human read: more promising than its rank.
- It handled code and long-context tasks reasonably well, but the memory task showed truncation and strict-format compliance is weak.
- Like the 27B distilled variant, it leaks a lot of reasoning text.
- Recommended role: keep as a code-and-analysis comparison model, not as a clean response model.

### `Qwen3.5-27B-4bit`

- Human read: the main issue is reasoning leakage on almost every task.
- Vision outputs are usable, but text and long-context practicality are poor because it rarely delivers just the answer.
- Recommended role: low priority for full baseline.

### `Qwen3.5-35B-A3B-4bit`

- Human read: middling text discipline, decent code, solid vision.
- The automatic score is fair enough here. It looks useful, but not clearly stronger than `gemma` or the 9B HighIQ variant for practical use.
- Recommended role: keep as a VLM comparison point.

### `Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-MLX-mxfp4`

- Human read: very similar profile to the plain 35B-A3B 4bit VLM.
- Capable on code and vision, weak on strict formatting and clean end-user response style.
- Recommended role: keep only if you want to compare these two 35B-A3B VLM variants directly.

### `Qwen3.5-9B-MLX-4bit`

- Human read: decent small coding-and-vision model, weak chat discipline.
- It did fine on basic code tasks and vision smoke, but text and long-context outputs are messy.
- Recommended role: fallback lightweight comparison, not top tier.

### `Qwen3.5-9B-mlx-vlm-mxfp4`

- Human read: weakest of the vision-capable small models in this set.
- It shows the same reasoning leakage pattern as the other Qwen VLMs, but with less practical upside.
- Recommended role: drop from deeper testing unless you specifically want a low-end VLM baseline.

## Revised Human Ranking

1. `gemma-4-26b-a4b-it-4bit`
2. `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`
3. `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`
4. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-4bit`
5. `MLX-Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-8bit`
6. `Qwen3.5-35B-A3B-4bit`
7. `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`
8. `Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-MLX-mxfp4`
9. `Huihui-Qwen3.5-27B-Claude-4.6-Opus-abliterated-mlx-8bit`
10. `Qwen3.5-9B-MLX-4bit`
11. `Qwen3.5-27B-4bit`
12. `Qwen3.5-9B-mlx-vlm-mxfp4`
13. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`

## Recommendation For The Next Pass

- Do not treat the automatic screening rank as the final baseline shortlist.
- Promote `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit` as a writing-focused finalist even though its code score is weak.
- Promote `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8` as a lightweight code-plus-vision finalist.
- Keep `gemma-4-26b-a4b-it-4bit` as the strongest all-round candidate.
- Exclude the unstable Huihui 8bit 35B-A3B variant from full baseline.
