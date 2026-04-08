# Findings

## Environment

- oMLX global settings: `/Users/dracoglasser/.omlx/settings.json`
- oMLX model settings: `/Users/dracoglasser/.omlx/model_settings.json`
- oMLX app support config: `/Users/dracoglasser/Library/Application Support/oMLX/config.json`
- oMLX MCP loader only accepts `mcp.json` or `mcp.yaml`
- Current MCP file path in settings points to `/Users/dracoglasser/.config/omlx/mcp.toml`
- Current MCP initialization is failing at server startup because the file is parsed as JSON

## API / Capability Facts

- `/v1/models/status` exposes model type, path, estimated size, max context window, and max tokens
- `/v1/models/{model_id}/unload` exists for explicit unload control
- Request-level overrides exist for `temperature`, `top_p`, and `max_tokens`
- Server-side model settings support model-level overrides for:
  `max_context_window`, `max_tokens`, `temperature`, `top_p`, `top_k`, `repetition_penalty`, and some advanced flags
- oMLX can transiently drop HTTP connections during unload/reload windows; retry logic is needed around unload and global sampling restore

## Installed Model Facts

- oMLX currently reports 13 installed models
- Metadata reports 3 `llm` models and 10 `vlm` models
- Vision capability still requires runtime smoke validation, not metadata-only trust

## OSS Agent Findings

- Original `claude` CLI is unreliable with local oMLX model routing on this machine
- `aider` can talk to oMLX, but it is not a strong fit for CC-style staged baton work
- `openclaude` is installable locally and works against `OPENAI_BASE_URL=http://127.0.0.1:8000/v1`
- `openclaude --print` succeeds for both Qwen 9B and Huihui 35B via the local OpenAI-compatible route
- The current best duo arrangement is:
  - 9B as scout / handoff generator
  - 35B as final closer / test runner

## Prompt-Tuning Findings

- Letting the 9B directly edit files wastes time and can hit timeout ceilings
- Constraining the 9B to read-only scouting sharply improves latency and handoff quality
- Giving the 35B explicit closer instructions plus one visible test run improves first-pass correctness
- OpenClaude + tuned prompts moved the duo from failing the earlier duel to passing visible and hidden tests cleanly
