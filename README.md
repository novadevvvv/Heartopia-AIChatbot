# Heartopia AI Chatbot

Automates in-game chat replies for Heartopia by:
- reading chat bubbles from a screenshot region (vision model),
- mapping messages into role-aware chat history,
- generating a short in-character reply with Groq,
- sending the reply back through UI automation.

## Requirements

- Windows (PowerShell commands below assume Windows)
- Python 3.10+
- A Groq API key
- Heartopia running in a stable window/layout

## 1. Clone and install

```powershell
git clone <your-repo-url>
cd Heartopia-AIChatbot
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure environment variables

Copy `.env.example` to `.env` and fill values:

```powershell
Copy-Item .env.example .env
```

Minimum required:

```env
heartopiaChatAPI=your_groq_api_key_here
```

Optional test toggles:

```env
RUN_CHAT_TESTS=0
RUN_VISION_TESTS=0
# HEARTOPIA_DEBUG_CROPS_DIR=debug_crops
```

## 3. First run calibration (required)

On first run, the bot asks you to position your mouse and press Enter for:
- `chat_button`
- `chat_bubble`
- `text_box`
- `send_button`
- `chat_area` (top-left then bottom-right)

These are saved to `config.json` and reused on next runs.

## 4. Anchor editor UI

Run the editor:

```powershell
python tools/anchor_editor/anchor_editor.py
```

Useful option:

```powershell
python tools/anchor_editor/anchor_editor.py --dir "your/screenshots/path"
```
(defaults to "tests/fixtures/screenshots")
For full controls and capture order, see:
- `tools/anchor_editor/README.md`

## 5. Run the bot

```powershell
python main.py
```

Notes:
- The script controls mouse/keyboard via `pyautogui`.
- Keep Heartopia focused and UI layout consistent.
- Replies are chunked to 40 chars for in-game sending.

## 6. LLM-only console mode (no game automation)

```powershell
python llm_console.py
```

Commands:
- `/context <text>` replace system context
- `/exit` quit

## 7. Tests

Unit tests:

```powershell
python -m unittest tests.test_chat_parsing tests.test_chat_preprocess tests.test_side_inference -v
```

### Optional: live Groq chat integration test

Requires:
- `heartopiaChatAPI` set
- `RUN_CHAT_TESTS=1`

Run:

```powershell
$env:RUN_CHAT_TESTS="1"; python -m unittest tests.test_groq_chat_integration -v
```

### Optional: screenshot contract integration test

Requires:
- `heartopiaChatAPI` set
- `RUN_VISION_TESTS=1`
- `tests/fixtures/screenshots/manifest.json` populated
- Optional crop dump output: `HEARTOPIA_DEBUG_CROPS_DIR=debug_crops`

Run:

```powershell
$env:RUN_VISION_TESTS="1"; python -m unittest tests.test_screenshot_contract -v
```

## Troubleshooting

- `Missing dependency: No module named 'groq'`
  - Activate venv and reinstall: `pip install -r requirements.txt`
- Bot clicks wrong places
  - Delete `config.json` and rerun `python main.py` to recalibrate
- Tests are skipped
  - Check required env vars and toggles (`RUN_CHAT_TESTS`, `RUN_VISION_TESTS`)
