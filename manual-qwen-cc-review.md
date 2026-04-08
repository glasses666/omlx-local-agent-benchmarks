# Manual Qwen CC Review

Generated from [`qwen-cc-summary.json`](/Users/dracoglasser/自定程式/codex_playground/2026-04-08-1943-cinder-benchmark/results/qwen-cc-summary.json) after reading raw outputs from the Claude-Code-style benchmark layer.

## Scope

- This review is about the supplementary `qwen-cc` suite, not the main baseline/tuned leaderboard.
- The local Claude Code CLI was detected on this machine, but the tested models were still run through oMLX under Claude-Code-style prompts. They were not executed inside Anthropic Claude Code itself.
- The suite intentionally used a deterministic profile:
  - `temperature=0.0`
  - `top_p=0.9`
  - `top_k=0`
  - `repetition_penalty=1.0`
  - `max_tokens=384`

## Scoring Biases In This Layer

- The current code scorer still rejects otherwise correct answers that include `import re`.
- Several models lose points because they wrap a correct answer in commentary, fenced code, or extra formatting instead of returning only the artifact.
- `Qwen3.5-27B-4bit` is clearly over-ranked by the raw score because it still leaks a large `Thinking Process` block on tasks that were supposed to be terse.
- The `long_context` task is strict `exact_text`, so models that answered with the right token plus formatting were scored as zero.

## Best Huihui Model

### `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`

- This is the strongest Huihui variant in the CC-style layer.
- It followed the planning and review prompts cleanly.
- It produced the best actual patching behavior among Huihui models:
  - `notify_user` was fully correct.
  - `slugify` was semantically correct, but the scorer rejected `import re`.
  - `apply_discount` was genuinely wrong for the `percent=2` case because it still treated `percent` as a fraction instead of a whole-number percentage.
- Weakness:
  - It still framed the long-context answer instead of returning the bare token, so the strict scorer gave it `0`.
- Practical read:
  - Best Huihui for supervised code edits.
  - Still not fully disciplined enough for strict artifact-only workflows.

## Best Standard Qwen-Opus Model

### `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

- This is the better of the two non-Huihui `Qwen-Opus` models in the CC-style layer.
- It handled the plan, review-risk, and long-context constraint tasks well.
- Code quality was mixed:
  - `notify_user` was close but returned `guest` instead of `hello guest`.
  - `apply_discount` used the wrong percent interpretation.
  - `slugify` was truncated, not just mis-scored.
- Practical read:
  - Better as a repo-analysis / review / constraint-tracking model than as a direct patch generator.
  - It looks more useful for “inspect and explain” than “edit and return the final code.”

## Huihui Series Internal Ranking

1. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
2. `Huihui-Qwen3.5-27B-Claude-4.6-Opus-abliterated-mlx-8bit`
3. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-4bit`

Reasoning:

- `Huihui 35B A3B mlx 8bit` had the best practical patch quality even though one strict-format task failed.
- `Huihui 27B mlx 8bit` was better at plan/review/constraint retention, but its patch outputs were often truncated or too commentary-heavy.
- `Huihui 35B A3B 4bit` was fast and obedient on the first two tasks, but it wandered on the repo-constraint answer and still mixed explanation into bugfix outputs.

## Huihui vs Qwen-Opus

### Raw score summary

- Best Huihui: `51.66`
- Best Qwen-Opus: `55.55`

### Human interpretation

- The raw score slightly favors `Qwen-Opus`, but that gap is misleading.
- `Qwen-Opus` scored higher mainly because it preserved the exact long-context token better.
- `Huihui` was better on real editability and patch usefulness.
- If the task is:
  - review / analyze / keep repo constraints in mind: `Qwen-Opus` has an edge
  - actually produce a usable edit under supervision: `Huihui` has the edge

## Important Outlier

### `Qwen3.5-27B-4bit`

- The raw CC-style winner was `Qwen3.5-27B-4bit`.
- I would not treat it as the practical winner without a caveat.
- It solved more of the strict scoring logic than the others, but it still dumped large `Thinking Process` text on tasks where that was explicitly unwanted.
- Practical read:
  - Strong candidate if you tolerate verbose hidden-planning leakage.
  - Not the cleanest “drop-in Claude Code replacement” style model.

## Bottom Line

- Best Huihui for CC-style supervised coding:
  - `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- Best standard Qwen-Opus for CC-style analysis:
  - `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`
- Better series for actual patch generation:
  - `Huihui`
- Better series for review / analysis / constraint tracking:
  - `Qwen-Opus`
- Best raw scorer overall in this supplementary suite:
  - `Qwen3.5-27B-4bit`
- Best practical “Huihui vs Qwen-Opus” answer:
  - If you want a coding sidekick that actually edits, pick the best `Huihui`.
  - If you want a reviewer/explainer that keeps instructions straighter, pick the best `Qwen-Opus`.
