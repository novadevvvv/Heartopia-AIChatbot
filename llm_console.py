import json

from src.ai.groq import getResponse


DEFAULT_CONTEXT = (
    "Roleplay as a casual 15-year-old girl playing Heartopia; "
    "reply in short (0-60 character) in-game chat style with light slang and occasional emojis, "
    "no narration, no meta commentary, never mention being an AI, stay in character."
)


def _extract_text(response: dict) -> str:
    try:
        return response["choices"][0]["message"]["content"].strip()
    except Exception:
        return json.dumps(response)


def main() -> None:
    print("LLM-only test mode")
    print("Type /exit to quit, /context <text> to override context.")
    context = DEFAULT_CONTEXT

    while True:
        prompt = input("you> ").strip()
        if not prompt:
            continue
        if prompt.lower() == "/exit":
            break
        if prompt.startswith("/context "):
            context = prompt.replace("/context ", "", 1).strip() or DEFAULT_CONTEXT
            print("context updated")
            continue

        response = getResponse(prompt, context)
        print(f"bot> {_extract_text(response)}")


if __name__ == "__main__":
    main()
