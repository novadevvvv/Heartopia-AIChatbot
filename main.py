import json
from time import sleep as wait
from src.log import log
from src.heartopia.interfacing import sendChat, getChat
from src.ai.groq import getResponse, imageToText

player_context = set()  # Track only unique player messages

log("Bot started, monitoring chat...")

while True:
    wait(2)
    raw_chat = getChat()  # Might return JSON, text, or a mix

    # Parse JSON safely
    try:
        messages = json.loads(raw_chat)
        if not isinstance(messages, list):
            messages = [messages]
    except json.JSONDecodeError:
        messages = [line.strip() for line in raw_chat.splitlines() if line.strip()]

    for msg_obj in messages:
        # Determine type
        if isinstance(msg_obj, dict):
            user = msg_obj.get("user", "unknown")
            msg_text = msg_obj.get("message")
            msg_image = msg_obj.get("image")
        elif isinstance(msg_obj, str):
            user = "player"  # fallback
            msg_text = msg_obj
            msg_image = None
        else:
            continue

        # Skip invalid text
        if not isinstance(msg_text, str):
            continue
        msg_text = msg_text.strip()
        if not msg_text:
            continue

        # Use a tuple of (user, text) to avoid duplicates
        msg_id = (user, msg_text)
        if msg_id in player_context:
            continue  # Already responded

        player_context.add(msg_id)
        log(f"New player message detected from {user}: {msg_text}")

        # Handle image
        if msg_image:
            try:
                img_text = imageToText(msg_image)
                msg_text += f" {img_text}"
            except Exception as e:
                log(f"Failed to process image: {e}")

        # Generate AI response
        try:
            ai_response = getResponse(
                msg_text,
                "Roleplay as a casual 15-year-old girl playing Heartopia; "
                "reply in short (0–60 character) in-game chat style with light slang and occasional emojis, "
                "no narration, no meta commentary, never mention being an AI, stay in character."
            )
            reply_content = ai_response["choices"][0]["message"]["content"].strip()
            sendChat(reply_content)
            log(f"Sent AI reply: {reply_content}")
        except Exception as e:
            log(f"Failed to generate/send AI response: {e}")
