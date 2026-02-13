# Testing

## Parser Unit Tests

Run:

```powershell
python -m unittest tests.test_chat_parsing tests.test_chat_preprocess -v
```

These tests validate:
- output format/schema
- fallback parsing behavior
- left/right filtering logic (`left` is treated as inbound player chat)
- deterministic screenshot preprocessing crop (message list only)

## Screenshot Integration Tests (Optional)

1. Put screenshots in `tests/fixtures/screenshots/`.
2. Copy `tests/fixtures/screenshots/manifest.example.json` to `tests/fixtures/screenshots/manifest.json`.
3. Fill expected values per screenshot.
4. Set env vars:
   - `heartopiaChatAPI`
   - `RUN_VISION_TESTS=1`
   - Optional for crop debugging: `HEARTOPIA_DEBUG_CROPS_DIR=debug_crops`

Run:

```powershell
python -m unittest tests.test_screenshot_contract -v
```

## Groq Chat Integration Tests (Optional)

1. Set env vars:
   - `heartopiaChatAPI`
   - `RUN_CHAT_TESTS=1`

Run:

```powershell
python -m unittest tests.test_groq_chat_integration -v
```

## LLM-Only Console Mode

Run:

```powershell
python llm_console.py
```

Use:
- `/context <text>` to replace system context
- `/exit` to quit
