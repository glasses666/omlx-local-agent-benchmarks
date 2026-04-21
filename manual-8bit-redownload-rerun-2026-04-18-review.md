# Manual 8bit Redownload Rerun 2026-04-18 Review

Generated after the 8bit redownload rerun captured in `results/manual-8bit-redownload-rerun-2026-04-18-index.json`.

This note summarizes the corrected second pass on the two 8bit variants that had previously failed with immediate 500 errors:

- `Qwen3.6-35B-A3B-8bit`
- `supergemma4-26b-abliterated-multimodal-mlx-8bit`

Ignored raw JSON outputs were written to:

- `results/manual-8bit-redownload-rerun-2026-04-18-index.json`
- `results/manual-Qwen3.6-35B-A3B-8bit-screening-summary.json`
- `results/manual-Qwen3.6-35B-A3B-8bit-qwen_cc-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-8bit-screening-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-8bit-full-summary.json`

## Environment Notes

- Backend under test: main oMLX on `http://127.0.0.1:8000`
- Generated-at marker from the rerun index: `2026-04-18T04:02:40Z`
- Trigger for the rerun: local download refresh after the first batch showed immediate 500s
- Root-backed `powermetrics` was captured again for the deeper rerun suites

## Headline Scores

| Model | Suite | Score | Notes |
| --- | --- | ---: | --- |
| `Qwen3.6-35B-A3B-8bit` | `screening` | `68.33` | Recovered completely from the initial 500-only state |
| `Qwen3.6-35B-A3B-8bit` | `qwen_cc` | `40.55` | Usable, but materially weaker than its 4bit sibling in CC-style scoring |
| `supergemma4-26b-abliterated-multimodal-mlx-8bit` | `screening` | `43.33` | Now runnable, but no longer looked exceptional in screening |
| `supergemma4-26b-abliterated-multimodal-mlx-8bit` | `full` | `63.06` | Functional, but did not beat the corresponding 4bit result |

## What the rerun proved

### The first-pass 500s were operational, not final quality verdicts

After refreshing the local downloads, both models passed minimal real completions and then completed deeper suite runs. That establishes a clear operational lesson:

- inventory discovery can succeed even when the local model payload is not healthy enough for real completions
- immediate 500s with near-idle power draw can indicate an incomplete/bad local download, not just a bad runtime or bad model family

### `Qwen3.6-35B-A3B-8bit` recovered, but did not become the new CC-style leader

Rerun result:
- `screening`: `68.33`
- `qwen_cc`: `40.55`

Interpretation:
- the model was genuinely runnable after download repair
- it kept strong instruction/chat discipline in the CC-style suite
- strict code output remained weak (`code = 11.11` in the rerun `qwen_cc` pass)
- it still lagged behind the earlier `Qwen3.6-35B-A3B-4bit` CC-style result (`51.66`)
- it also remained well behind the current tracked Qwen-family CC-style leader (`Qwen3.5-27B-4bit`, `72.22`)

Power note:
- average combined package power during rerun `qwen_cc`: about `20.93W`
- this is a real loaded-inference profile, unlike the earlier failing near-idle run

### `supergemma4-26b-abliterated-multimodal-mlx-8bit` recovered, but still did not beat the 4bit variant

Rerun result:
- `screening`: `43.33`
- `full`: `63.06`

Interpretation:
- the model was also genuinely runnable after download repair
- it kept the same broad shape as the 4bit version: useful vision/tool behavior, middling instruction precision
- but it still did not outperform the corresponding 4bit full-suite score (`64.17`)
- it also stayed well below the tracked Gemma-family leader (`gemma-4-31b-it-8bit`, `77.25`)

Power note:
- average combined package power during rerun `full`: about `26.77W`
- wall time was longer than the 4bit sibling (`153.48s` vs `107.97s`)

## Practical conclusions from the rerun

1. The earlier 500-only state should now be treated as an incomplete-download artifact.
2. Both 8bit models are now valid local candidates in the narrow sense that they can run and complete the benchmark suites.
3. Neither rerun 8bit variant earned a promotion over the stronger tracked leaders in its family.
4. In these specific benchmark layers, the corresponding 4bit variants remained more attractive performance/value points.

## Operational takeaway worth keeping

Before writing off a newly installed local model after immediate 500s, do this first:
1. refresh / verify the download
2. reload inventory
3. run a minimal real completion smoke test
4. only then rerun the deeper suite

That extra step turned a false-negative “dead model” diagnosis into a grounded “runnable but not top-tier” verdict.
