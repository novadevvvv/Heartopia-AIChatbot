from time import sleep as wait
from src.log import log
from src.heartopia.interfacing import sendChat, getChat
from src.ai.groq import getResponse
from src.chat.parsing import (
    build_llm_role_messages,
    get_inbound_player_messages,
    normalize_text_for_history,
    parse_chat_payload,
)

player_context = set()  # Track only unique player messages
ai_message_history = set()  # Track what the bot has sent to avoid self-replies


def _chunk_message(message: str, size: int = 40) -> list[str]:
    return [message[i:i + size] for i in range(0, len(message), size)] or [""]

log("Bot started, monitoring chat...")

while True:
    wait(2)
    raw_chat = getChat()
    parsed_chat = parse_chat_payload(raw_chat)
    role_messages = build_llm_role_messages(parsed_chat)
    inbound_messages = [
        msg
        for msg in get_inbound_player_messages(parsed_chat)
        if normalize_text_for_history(msg.get("message", "")) not in ai_message_history
    ]

    if not parsed_chat.get("chat_region_detected"):
        log("No chat region detected in OCR output; skipping this cycle.")
        continue

    for msg_obj in inbound_messages:
        user = msg_obj.get("user", "player")
        msg_text = msg_obj.get("message", "")

        # Use a tuple of (user, text) to avoid duplicates
        msg_id = (user, msg_text)
        if msg_id in player_context:
            continue  # Already responded

        player_context.add(msg_id)
        log(f"New player message detected from {user}: {msg_text}")

        # Generate AI response
        try:
            ai_response = getResponse(
                msg_text,
                "Roleplay as a casual 15-year-old girl playing Heartopia; "
                "reply in short (0–60 character) in-game chat style with light slang and occasional emojis, "
                "no narration, no meta commentary, never mention being an AI, stay in character.",
                conversation_messages=role_messages,
            )
            reply_content = ai_response["choices"][0]["message"]["content"].strip()
            sendChat(reply_content)
            for packet in _chunk_message(reply_content):
                normalized = normalize_text_for_history(packet)
                if normalized:
                    ai_message_history.add(normalized)
            log(f"Sent AI reply: {reply_content}")
        except Exception as e:
            log(f"Failed to generate/send AI response: {e}")
