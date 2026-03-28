# Step 04 — LLM Client Factory

## Scope

- Implement a configurable LLM client factory that instantiates the correct LangChain chat model based on `LLM_PROVIDER`
- Support Anthropic (Claude) and OpenAI as providers
- Define the interface that LLM nodes (Steps 05–06) will use

**Out of scope:** Prompt definitions (Steps 05–06). Structured output parsing (defined per-node).

## Context

The `parse_references` and `normalize_references` nodes both need an LLM to process text. The LLM provider must be configurable via environment variable (`LLM_PROVIDER` / `settings.llm_provider`) to allow switching between Anthropic and OpenAI without code changes.

LangChain provides `ChatAnthropic` and `ChatOpenAI` classes that share a common `BaseChatModel` interface, making provider switching transparent to the calling code.

## Requirements

### 1. Factory Function — `clients/llm.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/clients/llm.py`

```python
from langchain_core.language_models import BaseChatModel


def get_llm() -> BaseChatModel:
    """Return a configured LLM instance based on LLM_PROVIDER setting."""
```

**Behavior:**

1. Read settings: `settings.llm_provider`, `settings.llm_model`, `settings.llm_temperature`, and the relevant API key
2. Instantiate the correct class:

| `settings.llm_provider` | Class | API Key Setting |
|-----------------|-------|-----------------|
| `"anthropic"` | `ChatAnthropic` from `langchain_anthropic` | `settings.anthropic_api_key` |
| `"openai"` | `ChatOpenAI` from `langchain_openai` | `settings.openai_api_key` |

3. Pass common parameters:
   - `model=settings.llm_model`
   - `temperature=settings.llm_temperature`
   - The API key via `.get_secret_value()` (parameter name varies by provider: `anthropic_api_key` vs `openai_api_key`)

4. Return the instance

**Example usage by a node:**

```python
from biblio_checker_worker.langgraph.clients.llm import get_llm

llm = get_llm()
response = llm.invoke(messages)
```

### 2. Provider-Specific Configuration

**Anthropic (`ChatAnthropic`):**
```python
ChatAnthropic(
    model=settings.llm_model,
    temperature=settings.llm_temperature,
    anthropic_api_key=settings.anthropic_api_key.get_secret_value(),
    max_tokens=4096,
)
```

**OpenAI (`ChatOpenAI`):**
```python
ChatOpenAI(
    model=settings.llm_model,
    temperature=settings.llm_temperature,
    openai_api_key=settings.openai_api_key.get_secret_value(),
)
```

### 3. Error Handling

- If `settings.llm_provider` is not `"anthropic"` or `"openai"`, raise `ValueError(f"Unsupported llm_provider: {provider}")`.
- If the required API key is empty, the config validator from Step 01 will catch this at startup. The factory does NOT need to validate again.

### 4. Caching

The factory MUST NOT cache the LLM instance at module level. It should create a new instance on each call. This ensures:
- Test isolation (tests can override settings between calls)
- No stale configuration if settings change

If performance becomes a concern, caching can be added later with explicit cache invalidation.

### 5. Structured Output Support

Both `ChatAnthropic` and `ChatOpenAI` support the `.with_structured_output(schema)` method from `BaseChatModel`. Nodes that need structured output (Steps 05–06) will call:

```python
llm = get_llm()
structured_llm = llm.with_structured_output(MyPydanticModel)
result = structured_llm.invoke(messages)
```

The factory does NOT apply `.with_structured_output()` — that is the responsibility of each node.

### 6. Logging

Log at INFO level when creating a new LLM instance:
- `"llm_client_created"` with `provider`, `model`, `temperature`

Logger name: `"biblio_checker_worker.langgraph.clients.llm"`

## Acceptance Criteria

- [ ] `get_llm()` returns `BaseChatModel` instance
- [ ] When `LLM_PROVIDER="anthropic"`, returns `ChatAnthropic` with correct API key and model
- [ ] When `LLM_PROVIDER="openai"`, returns `ChatOpenAI` with correct API key and model
- [ ] Raises `ValueError` for unsupported provider values
- [ ] Does NOT cache instances at module level
- [ ] Both providers support `.with_structured_output()` (verified by documentation, not tested here)
- [ ] Logs instance creation at INFO level
- [ ] Unit tests cover: anthropic provider, openai provider, unsupported provider

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `llm_provider` is empty string | Config validation from Step 01 catches this at startup (default is `"anthropic"`) |
| API key is invalid | LLM call will fail at invocation time (not at factory time). Error propagates through `run_langgraph_stage` as transient StageError. |
| Network timeout during LLM call | Not handled here — handled at the node level (Steps 05–06) |

## Dependencies

- **Depends on:** Step 01 (config settings, dependencies: `langchain-anthropic`, `langchain-openai`)
- **Informs:** Step 05 (parse_references uses LLM), Step 06 (normalize uses LLM)
