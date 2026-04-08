# Experiment Report 2026-04-09

## Objective

Measure which local oMLX models are most useful in practice, then improve a two-model coding baton so that a small scout model and a larger closer model behave more like a disciplined coding agent.

Primary emphasis for this report:

- screened local-model practicality
- Claude-Code-style coding behavior
- OSS agent backend selection
- prompt tuning for a `9B scout -> 35B closer` baton
- repo-edit reliability on benchmark-owned Python repositories

## Environment

- Backend: local oMLX server at `http://127.0.0.1:8000/v1`
- Admin API: enabled and used for sampling control plus model unload discipline
- Agent backend used for the final duo experiments: `openclaude`
- Sampling profile for the duo experiments:
  - `temperature=0.0`
  - `top_p=0.9`
  - `top_k=0`
  - `repetition_penalty=1.0`

Retained local models at the time of the final experiments:

- `gemma-4-26b-a4b-it-4bit`
- `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`
- `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit`
- `Qwen3.5-27B-4bit`

## Experiment Matrix

| Experiment | Purpose | Main conclusion |
| --- | --- | --- |
| Screening + manual review | Find practically useful models instead of trusting raw automatic scores | `gemma` remained the strongest general model; `Qwen 9B HighIQ` and `Huihui 35B mlx 8bit` were kept for coding work |
| Qwen/Huihui CC-style review | Compare Qwen-family and Huihui-family coding behavior | Best Huihui for coding sidekick use was `Huihui 35B mlx 8bit`; best standard Qwen-Opus for analysis was `MLX-Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-4bit` |
| Web truth test | Measure false-premise correction with live search | `Qwen 9B HighIQ` was the strongest model in this small misleading-fact web test |
| OSS backend migration | Replace brittle native Claude CLI routing with an OSS agent runtime | `openclaude` was the first practical fit; `aider` could talk to oMLX but was a worse Claude-Code-style harness |
| `issue_digest` duo duel | Tune the 9B+35B baton on a small repo-edit task | Final tuned duo passed visible and hidden tests cleanly |
| `release_audit` real repo duel | Test whether the tuned baton generalizes to a new repo-edit task | The tuned duo generalized and again passed visible and hidden tests cleanly |

## Model Conclusions

### Best single-model roles

| Use case | Best current pick | Why |
| --- | --- | --- |
| General local chat / writing / vision | `gemma-4-26b-a4b-it-4bit` | Best all-round practical output from the screened pool |
| Lightweight coding + search correction | `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8` | Fast, small, and strong on coding plus misleading-web-query correction |
| Claude-Code-style local coding sidekick | `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit` | Best practical closer and patch finisher among tested Huihui/Qwen-family coding variants |
| Writing-focused text model | `Josiefied-Qwen3-30B-A3B-abliterated-v2-8bit` | Stronger long-form writing character than its raw coding score suggests |

### Key Qwen/Huihui finding

The best practical split was not “one model does everything.” The best structure was:

- `Qwen 9B HighIQ` for scouting, extracting constraints, and handing off a compact plan
- `Huihui 35B mlx 8bit` for final edits, verification, and disciplined close-out

## OSS Backend Finding

The native local `claude` CLI route was too brittle for this machine. The important progression was:

1. Native `claude` CLI: unreliable local model routing
2. `aider`: usable transport, but not a strong CC-style baton harness
3. `openclaude`: stable OpenAI-compatible local routing, proper tool-driven coding workflow, and workable non-interactive command mode

This made `openclaude` the chosen OSS backend for the final coding baton experiments.

## Prompt-Tuning Finding

The most important prompt change was role separation:

- bad pattern: let the 9B directly edit and over-commit
- better pattern: force the 9B into a scout-only handoff role
- keep the 35B as final closer with an explicit visible-test run

This reduced wasted scout time and improved first-pass correctness.

## Repo-Edit Results

### Tuned issue-digest duel

| Metric | Team Duo | Team Codex |
| --- | --- | --- |
| Mode | `oss_openclaude_baton` | `direct_one_pass` |
| Visible tests | `3/3` | `3/3` |
| Hidden tests | `3/3` | `3/3` |
| Constraint violations | none | none |
| Wall time | `51.41s` | `0.00s` |

Duo timing breakdown:

- 9B scout handoff: `10.93s`
- 35B final close: `38.02s`

### Tuned release-audit real-repo duel

| Metric | Team Duo | Team Codex |
| --- | --- | --- |
| Mode | `oss_openclaude_baton` | `direct_one_pass` |
| Visible tests | `3/3` | `3/3` |
| Hidden tests | `3/3` | `3/3` |
| Constraint violations | none | none |
| Wall time | `52.47s` | `0.00s` |

Duo timing breakdown:

- 9B scout handoff: `7.44s`
- 35B final close: `45.02s`

## Interpretation

The final question was not whether the duo could beat Codex in a one-shot direct comparison. It did not. The more important question was whether the duo could be tuned into a genuinely usable local coding workflow.

The answer is yes:

- it generalized across two different small repo-edit tasks
- it passed visible and hidden tests in both tracked final runs
- the tuned baton no longer relied on brittle JSON-only handoffs
- the OSS backend (`openclaude`) made the workflow practical on this machine

## Limitations

- Results are from benchmark-owned small Python repositories, not a large production repo
- The local retained model pool changed during the day as weaker models were deleted
- The native `claude` CLI path remained unreliable, so the final recommendation is about `openclaude`, not Anthropic’s original local CLI behavior
- Tool-use and web-use results are supplementary; the strongest current result is the repo-edit baton, not a full autonomous agent benchmark

## Reproduction

Install the OSS runtime:

```bash
mkdir -p third_party/openclaude-runtime
cd third_party/openclaude-runtime
npm install @gitlawb/openclaude
```

Run the two tracked coding-baton benchmarks:

```bash
python3 run_benchmark.py cc-duo-duel
python3 run_benchmark.py cc-realrepo-duel
```

Run the harness test suite:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile run_benchmark.py omlx_benchmark/*.py tests/*.py
```

## Bottom Line

- Best single general model: `gemma-4-26b-a4b-it-4bit`
- Best lightweight local coding/search model: `Qwen 9B HighIQ`
- Best local closer model for CC-style coding: `Huihui 35B mlx 8bit`
- Best current local coding workflow: `openclaude` + `Qwen 9B scout` + `Huihui 35B closer`
