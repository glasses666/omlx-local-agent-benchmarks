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

## Installed Model Facts

- oMLX currently reports 13 installed models
- Metadata reports 3 `llm` models and 10 `vlm` models
- Vision capability still requires runtime smoke validation, not metadata-only trust
