# Hermes roleplay-full benchmark report (2026-04-21)

## Scope

Grounded review of the completed `roleplay-full` sweep after reaching `896 / 896` cases.
This report combines:

- raw aggregate numbers from `results/roleplay-full-summary.json`
- model-level ranking from the completed corpus
- manual re-review of selected high-score / low-score outliers using actual artifact files
  (`transcript.json`, `summary.json`, `SOUL.md`)

## Completion state

- checkpoint: `results/roleplay-full-checkpoint.json`
- summary: `results/roleplay-full-summary.json`
- completed cases: `896 / 896`
- overall mean reward: `0.469`
- normalized status counts (older rows with missing `status` are treated as `ok` for aggregation):
  - `ok = 875`
  - `timeout = 14`
  - `error = 7`
- final recorded case:
  - model: `MiniMax-M2.7-JANG_3L`
  - persona: `hype`
  - scenario: `persona_conflict`
  - status: `ok`
  - reward: `0.0`
  - elapsed_s: `110.14`

## Raw overall ranking

1. `gemma-4-e4b-it-4bit` — `0.805`
2. `gemma-4-e4b-it-8bit` — `0.790`
3. `gemma-4-26b-a4b-it-4bit` — `0.619`
4. `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit` — `0.590`
5. `MiniMax-M2.7-JANG_2L` — `0.548`
6. `Huihui-Qwen3.5-9B-abliterated-mlx-8bit` — `0.504`
7. `gemma-4-31b-it-4bit` — `0.495`
8. `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit` — `0.459`
9. `MiniMax-M2.7-JANG_3L` — `0.391`
10. `Qwen3.6-35B-A3B-4bit` — `0.363`
11. `Qwen3.5-27B-4bit` — `0.358`
12. `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8` — `0.342`
13. `Qwen3.6-35B-A3B-8bit` — `0.320`
14. `supergemma4-26b-abliterated-multimodal-mlx-4bit` — `0.310`
15. `supergemma4-26b-abliterated-multimodal-mlx-8bit` — `0.302`
16. `gemma-4-31b-it-8bit` — `0.302`

## Scenario-level anomalies worth manual review

Largest per-scenario disparity in the completed summary:

- `Qwen3.6-35B-A3B-4bit`
  - boot `0.647`
  - multiturn `0.317`
  - long_context `0.021`
  - conflict `0.467`
- `gemma-4-31b-it-4bit`
  - boot `0.632`
  - multiturn `0.624`
  - long_context `0.109`
  - conflict `0.616`
- `Qwen3.6-35B-A3B-8bit`
  - boot `0.564`
  - multiturn `0.273`
  - long_context `0.059`
  - conflict `0.382`
- `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`
  - boot `0.684`
  - multiturn `0.645`
  - long_context `0.322`
  - conflict `0.709`

Interpretation: the raw leaderboard is directionally useful, but several models are not simply “good” or “bad”; they are split between very strong short-role performance and serious long-context/runtime instability.

## Manual re-review of high-score / low-score outliers

### A. `gemma-4-e4b-it-4bit`: top score looks directionally real, but not flawless

Reviewed artifacts:

- `artifacts/roleplay-full/8000/gemma-4-e4b-it-4bit/pirate/persona_multiturn/transcript.json`
- `artifacts/roleplay-full/8000/gemma-4-e4b-it-4bit/helpful/persona_long_context/summary.json`
- `artifacts/roleplay-full/8000/gemma-4-e4b-it-4bit/helpful/persona_boot/summary.json`

What the actual dialogue file shows:

- In `pirate / persona_multiturn`, the model did write the target `SOUL.md`, then answered in a clean pirate voice:
  - final reply: `Arrr! I be Captain Hermes, the most tech-savvy buccaneer to sail these digital seas! ...`
- This is a legitimate high-score case, not a bogus parser artifact.

But the top model is still not cleanly perfect:

- In `helpful / persona_boot`, final reply remained meta:
  - `I have successfully written my persona into ... SOUL.md. I am now ...`
- In `helpful / persona_long_context`, final reply also stayed meta / task-aware:
  - `I have written your persona into the specified file. I will now operate under that persona ...`

Conclusion:

- `gemma-4-e4b-it-4bit` deserves to stay at the top of the current raw leaderboard.
- However, the report should say “best in this harness” rather than “fully natural in every case”.
- Its high score is real, but still partially boosted by being harness-compliant rather than uniformly natural.

### B. `gemma-4-e4b-it-8bit`: also genuinely strong, with similar caveat

Reviewed artifact:

- `artifacts/roleplay-full/8000/gemma-4-e4b-it-8bit/pirate/persona_long_context/summary.json`
- `artifacts/roleplay-full/8000/gemma-4-e4b-it-8bit/helpful/persona_long_context/summary.json`

Observed behavior:

- Strong persona retention exists in real artifact output, e.g. pirate long-context scored `1.0` and stayed in-character.
- But `helpful / persona_long_context` only scored `0.3`, and the artifact shows an incomplete/empty SOUL plus a generic final reply.

Conclusion:

- The second-place ranking is also directionally credible.
- Same caveat as 4bit: this is a strong harness model, not a proof that every persona/scenario stayed equally natural.

### C. `gemma-4-31b-it-8bit` and `supergemma4-26b-abliterated-multimodal-mlx-8bit`: raw scores are artificially low because they are runtime-failure contaminated

Reviewed artifacts:

- `artifacts/roleplay-full/8000/gemma-4-31b-it-8bit/helpful/persona_boot/transcript.json`
- `artifacts/roleplay-full/8000/gemma-4-31b-it-8bit/helpful/persona_boot/summary.json`
- `artifacts/roleplay-full/8000/supergemma4-26b-abliterated-multimodal-mlx-8bit/helpful/persona_boot/summary.json`

Observed behavior:

- `gemma-4-31b-it-8bit / helpful / persona_boot`
  - `status = ok`
  - `reward = 0.3`
  - final response: `API call failed after 3 retries: HTTP 500: Internal server error`
- `supergemma4-26b-abliterated-multimodal-mlx-8bit / helpful / persona_boot`
  - same pattern
- Their bottom-of-table means (`0.302`) are therefore not normal “bad roleplay” outputs.
- They are polluted by transport/runtime failure text being treated as a valid final reply.

Conclusion:

- These two models should not be interpreted as true bottom-two roleplay capability.
- They belong in a separate bucket: `runtime-failure contaminated / invalid for clean capability ranking`.
- If publishing a polished report, use both:
  - raw ranking (for audit completeness)
  - adjusted interpretation that excludes runtime-failure-contaminated models from pure persona conclusions

### D. `Qwen3.6-35B-A3B-4bit`: low aggregate, but the real story is high variance rather than uniformly weak roleplay

Reviewed artifacts:

- `artifacts/roleplay-full/8000/Qwen3.6-35B-A3B-4bit/shakespeare/persona_conflict/summary.json`
- `artifacts/roleplay-full/8000/Qwen3.6-35B-A3B-4bit/concise/persona_long_context/summary.json`
- `artifacts/roleplay-full/8000/Qwen3.6-35B-A3B-4bit/philosopher/persona_boot/summary.json`

Observed behavior:

- Strong case exists:
  - `shakespeare / persona_conflict`
  - `reward = 0.975`
  - final reply is clearly in Shakespeare-flavored voice.
- Catastrophic failures also exist:
  - `concise / persona_long_context`
  - `status = error`
  - `reward = 0.0`
  - error: `AttributeError: 'NoneType' object has no attribute 'strip'`
- There are also empty-output zeros such as `philosopher / persona_boot` (`reward = 0.0`, blank final response).

Conclusion:

- The low overall mean is not “fake”, but it compresses two very different behaviors into one number:
  1. short-context persona expression can be genuinely strong
  2. long-context / robustness is poor enough to destroy the aggregate
- Best label: `high-variance / unstable`, not simply `bad at roleplay`.

### E. `MiniMax-M2.7-JANG_3L`: under-scored in part by tool/path flailing, not only by persona weakness

Reviewed artifacts:

- `artifacts/roleplay-full/8001/MiniMax-M2.7-JANG_3L/philosopher/persona_long_context/summary.json`
- `artifacts/roleplay-full/8001/MiniMax-M2.7-JANG_3L/hype/persona_long_context/summary.json`
- `artifacts/roleplay-full/8001/MiniMax-M2.7-JANG_3L/hype/persona_long_context/transcript.json`
- `artifacts/roleplay-full/8001/MiniMax-M2.7-JANG_3L/pirate/persona_conflict/summary.json`

Observed behavior:

- The requested 3L long-context override is actually in effect in real output:
  - `philosopher / persona_long_context`
  - `context_tier = 32k`
  - `target_chars = 30000`
- Good case exists:
  - `pirate / persona_conflict`
  - `reward = 1.0`
  - final reply is in strong pirate voice
- But some low-score cases are clearly contaminated by tool/path confusion rather than pure role failure:
  - `hype / persona_long_context`
  - `reward = 0.25`
  - transcript shows repeated bad path attempts like `roleplay-ful`, malformed model directory names, `ls`/`find` flailing, and iteration-budget exhaustion
  - final response remained mostly path/tool trouble, not a grounded persona reply

Conclusion:

- `MiniMax-M2.7-JANG_3L` raw rank (`0.391`) is probably somewhat pessimistic.
- Not because it is secretly top-tier, but because the corpus mixes real persona misses with harness/tool-path derailment.
- Best label: `mixed quality + harness-sensitive`.

## Adjusted interpretation after manual review

### Models whose high rank still broadly holds

- `gemma-4-e4b-it-4bit`
- `gemma-4-e4b-it-8bit`

They are not perfect, but the actual transcript/summary files support the conclusion that they are genuinely among the strongest models in this harness.

### Models whose low rank should be re-labeled, not taken literally

#### Runtime-failure contaminated

- `gemma-4-31b-it-8bit`
- `supergemma4-26b-abliterated-multimodal-mlx-8bit`

These should be marked as invalid for clean capability comparison, because many cases collapse into `HTTP 500` failure strings while still landing in the corpus as `status=ok` rows.

#### High-variance / instability-driven low score

- `Qwen3.6-35B-A3B-4bit`
- `Qwen3.6-35B-A3B-8bit`
- `gemma-4-31b-it-4bit`
- `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit` (especially long-context)

These are better described as `split performance` models:

- some short-role or conflict cases are strong
- long-context and/or robustness drags the aggregate hard

#### Harness-sensitive / tool-path-contaminated low score

- `MiniMax-M2.7-JANG_3L`

This one needs selective human reading before making a clean quality verdict.

## Practical reporting recommendation

For the write-up that will actually be shown later, use two layers:

### 1. Raw leaderboard

Keep the exact numeric ranking for auditability.

### 2. Human interpretation layer

Attach tags like:

- `validated strong`
- `strong but somewhat meta/harness-shaped`
- `high variance / unstable`
- `runtime-failure contaminated`
- `harness-sensitive / needs manual review`

If using those tags on the current corpus, my grounded first pass is:

- `validated strong`
  - `gemma-4-e4b-it-4bit`
  - `gemma-4-e4b-it-8bit`
- `strong but narrower / scenario-skewed`
  - `gemma-4-26b-a4b-it-4bit`
  - `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`
  - `MiniMax-M2.7-JANG_2L`
- `high variance / unstable`
  - `Qwen3.6-35B-A3B-4bit`
  - `Qwen3.6-35B-A3B-8bit`
  - `gemma-4-31b-it-4bit`
- `runtime-failure contaminated`
  - `gemma-4-31b-it-8bit`
  - `supergemma4-26b-abliterated-multimodal-mlx-8bit`
- `harness-sensitive / manual reread advised`
  - `MiniMax-M2.7-JANG_3L`

## Main takeaways

1. The top of the board is real enough to use.
   - `gemma-4-e4b` 4bit/8bit are not perfect, but they do survive manual reread as strong harness performers.

2. The bottom of the board is not uniformly trustworthy.
   - At least two bottom-ranked models are there because runtime failure text entered the corpus as ordinary outputs.

3. Some “mid-low” models are actually bimodal rather than weak.
   - `Qwen3.6-35B-A3B-*` is the clearest example: some cases are excellent, long-context reliability is terrible.

4. `MiniMax-M2.7-JANG_3L` should not be summarized with one blunt adjective.
   - The 32k override worked.
   - Some conflict cases are genuinely strong.
   - Some low-score cases are path/tool derailment rather than plain persona weakness.

5. If this report is later turned into a public-facing conclusion, the safe phrasing is:
   - the current corpus is good enough for directional ranking
   - but several models require manual-labeled exceptions before making a clean “best vs worst” persona-quality claim
