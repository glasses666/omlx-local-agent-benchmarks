# Task Plan

## Goal

Build and run a safe, reproducible benchmark harness for local oMLX models with:

- staged screening and finalist comparison
- baseline and tuned profiles
- backup-first config handling
- explicit model unload discipline
- structured JSON/CSV/Markdown outputs

## Phases

| Phase | Status | Notes |
|---|---|---|
| Workspace setup and planning | in_progress | Create isolated workspace, gather reuse candidates |
| Harness implementation | pending | Tasks, profiles, runners, scoring, reports |
| Config backup and MCP repair | pending | Backup relevant files before any system mutation |
| Smoke validation | pending | Verify harness, unload cycle, MCP health handling |
| Stage 1 screening run | pending | Run all installed models through the light suite |
| Reporting and commit milestones | pending | Summaries, tables, git commits |

## Non-Negotiables

- Never modify oMLX config before backup.
- Keep only one model loaded at a time.
- If MCP remains unhealthy, continue other benchmark dimensions and mark tool-use deferred.
- Do not fabricate timings, tool calls, scores, or capabilities.

## Defaults

- Baseline sampling: `temperature=0.2`, `top_p=0.95`, `top_k=0`, `repetition_penalty=1.0`
- Baseline output cap: `max_tokens=1024` unless the task family requires a lower shared cap
- Main benchmark excludes global scheduler/cache tuning from the primary ranking
