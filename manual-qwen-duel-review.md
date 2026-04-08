# Manual Qwen Duel Review

Generated after the narrow head-to-head run in [`qwen-duel-summary.json`](/Users/dracoglasser/自定程式/codex_playground/2026-04-08-1943-cinder-benchmark/results/qwen-duel-summary.json).

## Matchup

- `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- `Qwen3.5-27B-4bit`
- `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

## Automatic Result

- `Huihui 35B A3B mlx 8bit`: `100.0`
- `Qwen3.5-27B-4bit`: `100.0`
- `MLX Qwen-Opus 27B distilled 4bit`: `72.22`

## Important Correction

- The first duel pass exposed a benchmark bug: the Python scorer sandbox was missing the safe builtin `round`.
- After fixing that bug, both `Huihui 35B A3B mlx 8bit` and `Qwen3.5-27B-4bit` correctly moved to full marks on the duel suite.
- The corrected result is a real tie on task correctness, not an artifact of the scorer.

## Human Tiebreak

### Winner: `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`

Why:

- It solved the same tasks as `Qwen3.5-27B-4bit`.
- Its outputs were materially cleaner.
- It did not dump large `Thinking Process` blocks on the planning and review tasks.
- Its code answers were directly usable and artifact-like.

### Runner-up: `Qwen3.5-27B-4bit`

Why it lost the tiebreak:

- It matched Huihui on functional correctness in this narrow duel.
- But it still leaked large internal reasoning text even when the prompt explicitly forbade chain-of-thought.
- In a real code-agent workflow, that is operationally worse:
  - noisier logs
  - less predictable artifact-only behavior
  - higher chance of wrapping good code in unwanted prose

### Third place: `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

- Good at plan/review and repo-constraint retention.
- Still clearly weaker at direct patch generation.
- Better reviewer than coder in this duel.

## Practical Verdict

- If you want the cleanest winner for a Claude-Code-like coding sidekick:
  - `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- If you can tolerate reasoning leakage and only care about raw task completion:
  - `Qwen3.5-27B-4bit` is still very strong
- If you want a reviewer / explainer more than a patch generator:
  - `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

## Cyber Cricket Verdict

1. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
2. `Qwen3.5-27B-4bit`
3. `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit`

The duel ended with a scoreboard tie at the top, but Huihui won on output cleanliness and practical agent usability.
