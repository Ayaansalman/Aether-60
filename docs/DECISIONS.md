# Architectural & Engineering Decisions

## ADR-001: Unified OpenAI-Compatible Adapter for LLM Model Integration

### Context
AETHER requires LLM planning and repair capabilities to generate GameIR specifications from user natural language prompts. Different deployment environments and evaluation stages may use distinct underlying LLM providers—such as OpenAI (`gpt-4o-mini`), Google Gemini (via its OpenAI-compatible endpoint `https://generativelanguage.googleapis.com/v1beta/openai/`), Tokenra (`https://tokenra.io/v1`, model `stealth/ox-alpha`), local inference engines (vLLM, Ollama), or an offline mock provider for automated testing and CI.

### Decision
We use a single, standardized OpenAI-compatible HTTP adapter (`OpenAICompatProvider`) alongside an offline `MockModelProvider` instead of binding the codebase to vendor-specific SDKs (e.g. `google-generativeai`, `openai`, `anthropic`).

### Rationale
1. **Zero Vendor Lock-In:** Any LLM service exposing a `/chat/completions` endpoint can be targeted immediately by configuring `MODEL_BASE_URL`, `MODEL_NAME`, and `MODEL_API_KEY` in `.env` without altering application code or installing vendor-specific packages.
2. **Simplified Dependency Footprint:** Relies only on standard synchronous `httpx` and `pydantic`.
3. **Environment-Driven Switching:** The model can be dynamically switched through `.env` variables (`MODEL_PROVIDER=mock | openai_compat`).
4. **Deterministic Testing:** Offline test runners and automated CI environments use `MockModelProvider` requiring no API keys or internet access.
