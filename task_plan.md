# Task Plan

## Goal

Build and run a safe, reproducible benchmark harness for local oMLX models with:

- staged screening and finalist comparison
- baseline and tuned profiles
- backup-first config handling
- explicit model unload discipline
- structured JSON/CSV/Markdown outputs
- an OSS Claude-Code-style backend for the 9B+35B duo
- a more realistic repo-edit benchmark plus a publishable public experiment report

## Phases

| Phase | Status | Notes |
|---|---|---|
| Workspace setup and planning | completed | Existing benchmark workspace active on feature branch |
| Harness implementation | completed | Screening, duel, reporting, scoring, MCP handling landed |
| Config backup and MCP repair | completed | Runtime MCP JSON and backup manifests already in place |
| Smoke validation | completed | Test suite green; unload/retry logic added |
| Stage 1 screening run | completed | Screening, manual review, web tests, Qwen/Huihui duels done |
| OSS agent backend switch | completed | Replaced aider path with OpenClaude-backed baton flow |
| Duo prompt tuning | completed | 9B scout + 35B closer prompts materially improved first-pass reliability |
| Realistic repo-edit benchmark | completed | Added `release_audit` small repo and re-ran the tuned duo successfully |
| Public report and GitHub publishing | in_progress | Standard public report written; repository creation and push next |

## Non-Negotiables

- Never modify oMLX config before backup.
- Keep only one model loaded at a time.
- If MCP remains unhealthy, continue other benchmark dimensions and mark tool-use deferred.
- Do not fabricate timings, tool calls, scores, or capabilities.
- Treat transient oMLX disconnects as infrastructure noise and retry before failing the run.
- Keep the 9B scout lightweight; reserve final file writes and verification for the 35B closer.

## Defaults

- Baseline sampling: `temperature=0.2`, `top_p=0.95`, `top_k=0`, `repetition_penalty=1.0`
- Baseline output cap: `max_tokens=1024` unless the task family requires a lower shared cap
- Main benchmark excludes global scheduler/cache tuning from the primary ranking
- OSS duo backend: `openclaude` over local OpenAI-compatible oMLX endpoint
