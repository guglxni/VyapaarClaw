# LLM Configuration (LiteLLM)

VyapaarClaw is **provider-agnostic**. All LLM calls route through [LiteLLM](https://docs.litellm.ai/), so you can use any supported provider without vendor lock-in.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VYAPAAR_LLM_MODEL` | Yes* | LiteLLM model ID (e.g. `gpt-4o`, `azure/kimi-k2.5`) |
| `VYAPAAR_LLM_API_KEY` | Usually | API key for the provider |
| `VYAPAAR_LLM_BASE_URL` | Optional | Custom endpoint (Azure, Ollama, vLLM, etc.) |
| `VYAPAAR_LLM_API_VERSION` | Optional | Provider API version (Azure) |
| `VYAPAAR_DELEGATION_LLM_MODEL` | Optional | Cheaper model for sub-agents (defaults to `openai/gpt-4o-mini`) |
| `VYAPAAR_SECURITY_LLM_MODEL` | Optional | Model for Dual LLM security validation |

\* If unset, legacy `VYAPAAR_AZURE_OPENAI_*` vars are auto-migrated.

## Provider Examples

### OpenAI

```bash
VYAPAAR_LLM_MODEL=gpt-4o
VYAPAAR_LLM_API_KEY=sk-...
```

### Azure OpenAI

```bash
VYAPAAR_LLM_MODEL=azure/kimi-k2.5
VYAPAAR_LLM_API_KEY=<azure-key>
VYAPAAR_LLM_BASE_URL=https://your-resource.services.ai.azure.com/models
VYAPAAR_LLM_API_VERSION=2024-05-01-preview
```

### Anthropic

```bash
VYAPAAR_LLM_MODEL=anthropic/claude-sonnet-4-20250514
VYAPAAR_LLM_API_KEY=sk-ant-...
```

### Ollama (local)

```bash
VYAPAAR_LLM_MODEL=ollama/llama3
VYAPAAR_LLM_BASE_URL=http://localhost:11434
# No API key needed
```

### Groq

```bash
VYAPAAR_LLM_MODEL=groq/llama-3.3-70b-versatile
VYAPAAR_LLM_API_KEY=gsk_...
```

## Delegation Model

Sub-agents spawned for vendor due diligence and anomaly investigation use `VYAPAAR_DELEGATION_LLM_MODEL`. Set a cheaper model here to save cost on research tasks:

```bash
VYAPAAR_DELEGATION_LLM_MODEL=openai/gpt-4o-mini
```

OpenClaw `sessions.spawn` and bootstrap templates reference this variable.

## Legacy Azure Migration

If you have existing `VYAPAAR_AZURE_OPENAI_*` variables, they are automatically mapped:

| Legacy | Maps to |
|--------|---------|
| `VYAPAAR_AZURE_OPENAI_DEPLOYMENT` | `VYAPAAR_LLM_MODEL=azure/{deployment}` |
| `VYAPAAR_AZURE_OPENAI_API_KEY` | `VYAPAAR_LLM_API_KEY` |
| `VYAPAAR_AZURE_OPENAI_ENDPOINT` | `VYAPAAR_LLM_BASE_URL` |

No code changes needed — migration runs at config load time.

## Implementation

- `src/vyapaar_mcp/llm/client.py` — primary chat completions
- `src/vyapaar_mcp/llm/security_validator.py` — Dual LLM security tier
- `src/vyapaar_mcp/config.py` — `_migrate_legacy_llm_config()` validator
