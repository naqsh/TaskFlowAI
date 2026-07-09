# Local LLM Fallback — TaskFlow AI (TF-053)

## Overview

Privacy-sensitive and PII-classified AI requests route to a local Ollama instance instead of cloud LLM providers.

## Hardware Requirements

| Config | RAM | GPU | Expected Latency |
|---|---|---|---|
| Minimum (CPU) | 16 GB | None | 30–120s per request |
| Recommended | 32 GB | 8 GB VRAM | 5–15s per request |
| Optimal | 64 GB | 24 GB VRAM | 1–5s per request |

## Model

Default: **Llama 3.1** via Ollama (`llama3.1`)

```bash
ollama pull llama3.1
ollama serve  # default http://localhost:11434
```

## Configuration

| Setting | Default | Description |
|---|---|---|
| `LOCAL_LLM_ENABLED` | `false` | Enable local fallback provider |
| `LOCAL_LLM_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `LOCAL_LLM_MODEL` | `llama3.1` | Model name |
| `LOCAL_LLM_MAX_CONTEXT_TOKENS` | `4096` | Context window limit |

## Routing Rules

1. **PII classification**: Input containing `ssn`, `passport`, `credit card`, or `confidential_pii` → `force_local=true`
2. **Fallback order**: primary → gpt-4o-mini → local (when enabled)
3. **Context truncation**: Messages exceeding window are truncated with warning log

## Privacy Rules

- PII-classified content never sent to cloud providers when `LOCAL_LLM_ENABLED=true`
- Local inference keeps data on-premises
- Latency tracked separately via `local_llm_latency_seconds` histogram

## Files

- `backend/llm/local.py` — Ollama provider
- `backend/llm/router.py` — `force_local` routing
- `backend/agents/planner/node.py` — PII classification hook
