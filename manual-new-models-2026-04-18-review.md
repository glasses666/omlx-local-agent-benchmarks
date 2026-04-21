# Manual New Models 2026-04-18 Review

Generated after the 2026-04-18 new-model batch captured in `results/manual-new-models-2026-04-18-index.json`.

This note summarizes the first pass on four newly installed local models:

- `Qwen3.6-35B-A3B-4bit`
- `Qwen3.6-35B-A3B-8bit`
- `supergemma4-26b-abliterated-multimodal-mlx-4bit`
- `supergemma4-26b-abliterated-multimodal-mlx-8bit`

Ignored raw JSON outputs were written to:

- `results/manual-new-models-2026-04-18-index.json`
- `results/manual-Qwen3.6-35B-A3B-4bit-screening-summary.json`
- `results/manual-Qwen3.6-35B-A3B-4bit-qwen_cc-summary.json`
- `results/manual-Qwen3.6-35B-A3B-8bit-screening-summary.json`
- `results/manual-Qwen3.6-35B-A3B-8bit-qwen_cc-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-4bit-screening-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-4bit-full-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-8bit-screening-summary.json`
- `results/manual-supergemma4-26b-abliterated-multimodal-mlx-8bit-full-summary.json`

## Environment Notes

- Backend under test: main oMLX on `http://127.0.0.1:8000`
- Generated-at marker from the batch index: `2026-04-18T03:09:27Z`
- The batch reused the local benchmark harness and saved per-model manual summaries under ignored `results/`
- Real root-backed `powermetrics` was captured for the deeper `qwen_cc` / `full` suites where applicable

## Headline Scores

| Model | Suite | Score | Notes |
| --- | --- | ---: | --- |
| `Qwen3.6-35B-A3B-4bit` | `screening` | `60.83` | Strong screening debut; landed above the old finalist floor |
| `Qwen3.6-35B-A3B-4bit` | `qwen_cc` | `51.66` | Good instruction/chat discipline, weaker strict code delivery |
| `Qwen3.6-35B-A3B-8bit` | `screening` | `5.56` | Initial batch was unusable due to immediate 500s |
| `Qwen3.6-35B-A3B-8bit` | `qwen_cc` | `0.00` | Same failure mode in deeper Claude-Code-style prompts |
| `supergemma4-26b-abliterated-multimodal-mlx-4bit` | `screening` | `63.33` | Tied the current screening leader in the initial pass |
| `supergemma4-26b-abliterated-multimodal-mlx-4bit` | `full` | `64.17` | Strong vision/tool behavior, still behind the Gemma 4 family leader |
| `supergemma4-26b-abliterated-multimodal-mlx-8bit` | `screening` | `5.56` | Initial batch was unusable due to immediate 500s |
| `supergemma4-26b-abliterated-multimodal-mlx-8bit` | `full` | `5.56` | Same failure mode in the full suite |

## What the first pass actually showed

### 4bit variants were the real candidates

`Qwen3.6-35B-A3B-4bit` immediately looked viable:
- `screening`: `60.83`
- `qwen_cc`: `51.66`
- qualitative read: stronger as an analysis/review sidekick than as a strict code-output model

`supergemma4-26b-abliterated-multimodal-mlx-4bit` also looked viable:
- `screening`: `63.33`
- `full`: `64.17`
- qualitative read: useful multimodal generalist with strong vision/tool behavior, but not a new overall Gemma-family champion

### Both 8bit variants looked broken in the initial pass

At initial batch time, both new 8bit variants failed almost immediately on every real completion request:
- `Qwen3.6-35B-A3B-8bit`
- `supergemma4-26b-abliterated-multimodal-mlx-8bit`

Observed symptoms:
- immediate `500 Internal Server Error` on `/v1/chat/completions`
- negligible real power draw during the failing deeper suites
- no useful task-level scores beyond failure placeholders

At the time, this looked like runtime-level failure rather than poor model quality.

## Important retrospective note

A later rerun after refreshing the downloads established that these initial 8bit failures were not stable model-quality findings. They were artifacts of incomplete or bad local downloads.

That means this initial review should be read as:
- a real result for the two 4bit variants
- a failure-detection snapshot for the two 8bit variants
- **not** the final verdict on the 8bit models

See `manual-8bit-redownload-rerun-2026-04-18-review.md` for the corrected second pass.

## Practical conclusions from the first pass

1. The two 4bit variants were worth keeping in the active candidate pool immediately.
2. The two 8bit variants should not have been judged from the first pass alone because the failure mode was operational, not behavioral.
3. The initial batch still served a useful purpose: it exposed that inventory visibility does not guarantee a valid local model payload.
