import os
import requests
from ..log import log
from groq import Groq
import base64
from pathlib import Path
from ..env_loader import load_env_file
from ..heartopia.chat_preprocess import prepare_chat_message_list
from ..heartopia.side_inference import correct_message_sides

"""
Website: https://github.com/novadevvvv
Dependencies: "log.py"
Path: "src/ai/"
"""

apiEnv = "heartopiaChatAPI"
load_env_file()
apiKey = os.getenv(apiEnv)

if apiKey is None:
    log("Invalid API Key")
    exit()

log(f"Got API Key Starting With {apiKey[:10]}")

client = Groq(api_key=apiKey)

import base64
from PIL import Image
from io import BytesIO

def encode_image(image) -> str:
    """
    Accepts either:
    - file path (str)
    - PIL Image object
    Returns base64 string
    """
    if isinstance(image, str):
        with open(image, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    elif isinstance(image, Image.Image):
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    else:
        raise TypeError("encode_image expects a file path or PIL Image")

if not apiKey:
    raise RuntimeError(f"Environment variable '{apiEnv}' not set")

URL = "https://api.groq.com/openai/v1/chat/completions"

def getResponse(
    prompt: str,
    context: str,
    conversation_messages: list[dict[str, str]] | None = None,
) -> dict:

    model = "llama-3.3-70b-versatile"

    log(f"Creating Payload For `{model}`")

    messages = [{"role": "system", "content": context}]
    if conversation_messages:
        messages.extend(conversation_messages)
    else:
        messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages
    )

    log(f"Recieved Response Of `{len(response.model_dump())}` Objects.")

    return response.model_dump()

def imageToText(image: str) -> str:
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    log(f"Creating Payload For `{model}`")
    cropped_image, classifier_hints = prepare_chat_message_list(image)
    _maybe_dump_debug_crop(image, cropped_image)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are extracting Heartopia chat from a cropped image that already contains only the chat history message-list area. "
                    "Return strict JSON only (no markdown, no prose). "
                    "Use exactly this schema: "
                    "{\"chat_region_detected\": <true|false>, \"messages\": [{\"side\": \"left|right|unknown\", \"x_min\": <0.0-1.0>, \"x_max\": <0.0-1.0>, \"x_center\": <0.0-1.0>, \"y_center\": <0.0-1.0>, \"user\": \"<name or unknown>\", \"message\": \"<text>\"}]}. "
                    "Rules: left side means other player, right side means current player (AI). "
                    "Only include actual chat bubbles visible in this cropped message-list image. "
                    "If a left chat bubble has an avatar/name and text, set user to the displayed name and message to bubble text. "
                    "If a right chat bubble has no shown username, set user to \"unknown\" and message to bubble text. "
                    "x_min and x_max are required for each bubble and must be normalized bubble bounds relative to cropped width. "
                    "x_center is required and should match the bubble center position. "
                    "y_center is required and should be normalized bubble center position relative to cropped height. "
                    "Preserve visual top-to-bottom order for the bubbles in the message list only. "
                    "If no chat bubbles are visible, return chat_region_detected=false and messages=[]. "
                    "If text is unreadable, use an empty messages array."
                )
            },
            {
                "role": "user",
                "content": "What's in this image?"
            },
            {
                "role": "user",
                "content": [
                    {  # wrap the image in a list
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(cropped_image)}"
                        }
                    }
                ]
            }
        ]
    )

    log(f"Received Response With {len(response.choices)} Choices.")
    raw_payload = response.choices[0].message.content
    return correct_message_sides(raw_payload, cropped_image, classifier_hints=classifier_hints)


def _maybe_dump_debug_crop(image: str | Image.Image, cropped_image: Image.Image) -> None:
    out_dir = os.getenv("HEARTOPIA_DEBUG_CROPS_DIR")
    if not out_dir:
        return
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(image, str):
        stem = Path(image).stem
    else:
        stem = "in_memory"

    out_path = target_dir / f"{stem}_crop.png"
    cropped_image.save(out_path)
