# oMLX Local Agent Benchmarks

Benchmark harness and experiment logs for comparing local oMLX-served models, with a focus on Claude-Code-style coding behavior and lightweight multi-model baton flows.

## Scope

This repository contains:

- a reproducible oMLX benchmark harness
- benchmark-owned small Python repo-edit tasks
- model screening and manual-review notes
- dual-agent coding experiments using:
  - `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`
  - `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- an OSS Claude-Code-style backend migration from brittle native CLI routing to `openclaude`

## Current Findings

- Best general local model from the screened pool: `gemma-4-26b-a4b-it-4bit`
- Best lightweight coding and web-truth model: `Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8`
- Best Claude-Code-style local sidekick: `Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit`
- Best duo structure so far:
  - 9B as scout / handoff generator
  - 35B as final closer / test runner
  - `openclaude` as the OSS agent runtime

## Benchmark Test Machine

Unless a report says otherwise, the benchmark runs and experiment notes in this repository were produced on this machine:

- Hardware: MacBook Pro
- Chip: Apple M5 Max
- Memory: 128 GB unified memory
- Operating system: macOS 26.4

Full reference:

- [Test Machine](TEST_MACHINE.md)

## Key Report

- [Experiment Report 2026-04-09](EXPERIMENT_REPORT_2026-04-09.md)

Supporting tracked notes:

- [Manual Screening Review](manual-screening-review.md)
- [Manual Qwen CC Review](manual-qwen-cc-review.md)
- [Manual Qwen Duel Review](manual-qwen-duel-review.md)
- [Manual JANG 2L Long Review](manual-jang-2l-long-review.md)
- [Manual New Models 2026-04-18 Review](manual-new-models-2026-04-18-review.md)
- [Manual 8bit Redownload Rerun 2026-04-18 Review](manual-8bit-redownload-rerun-2026-04-18-review.md)
- [Manual JANG 3L Long Review](manual-jang-3l-long-review.md)

## Reproduce

Prerequisites:

- local oMLX server running at `http://127.0.0.1:8000/v1`
- oMLX admin endpoint enabled
- retained local models loaded into oMLX inventory
- Node.js and npm if you want to use the `openclaude` backend

Install the OSS agent runtime used in the current duet experiments:

```bash
mkdir -p third_party/openclaude-runtime
cd third_party/openclaude-runtime
npm install @gitlawb/openclaude
```

Run the main benchmark commands:

```bash
python3 run_benchmark.py screening
python3 run_benchmark.py qwen-cc
python3 run_benchmark.py cc-duo-duel
python3 run_benchmark.py cc-realrepo-duel
```

Run the verification suite:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile run_benchmark.py omlx_benchmark/*.py tests/*.py
```

## Repository Layout

- `omlx_benchmark/`: harness code
- `benchmark_projects/`: benchmark-owned repo tasks and Codex reference solutions
- `tests/`: harness tests
- `profiles.json`: sampling and duel profiles
- `tasks.json`: model task definitions for screening and related suites

Ignored runtime outputs:

- `results/`
- `reports/`
- `runs/`
- `artifacts/`
- `logs/`
- `backups/`
- `third_party/`
