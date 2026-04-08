# Progress

## Session Log

- Created isolated benchmark workspace and initialized a local git repository.
- Confirmed current oMLX settings, model settings, MCP config path, and model inventory.
- Confirmed current MCP config path is invalid for oMLX's loader because it expects JSON or YAML, not TOML.
- Identified request-level sampling overrides and model unload API support.
- Built and ran the full screening harness, manual reviews, Qwen/Huihui coding duels, and web-truth tests.
- Added a benchmark-owned `issue_digest` repo task plus hidden tests for one-shot duo-vs-Codex evaluation.
- Switched the duo backend from simulated baton / aider experiments to `openclaude`.
- Tuned the duo prompts into a `9B scout -> 35B closer` structure.
- Verified the tuned OpenClaude duo now passes `3/3` visible and `3/3` hidden tests on the current duel task.
- Added a second benchmark-owned repo-edit task, `release_audit`, and verified the tuned duo also passes `3/3` visible and `3/3` hidden there.
- Wrote a tracked public-facing report and README for GitHub publication.
- Added retry handling around unload and global sampling restore to reduce oMLX transient disconnect failures.
- Next: create the public GitHub repository and push the current benchmark branch contents.
