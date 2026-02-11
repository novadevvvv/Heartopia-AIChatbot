import os
import requests
from ..log import log
from groq import Groq
import base64

"""
Website: https://github.com/novadevvvv
Dependencies: "log.py"
Path: "src/ai/"
"""

apiEnv = "heartopiaChatAPI"
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

def getResponse(prompt: str, context: str) -> dict:

    model = "llama-3.3-70b-versatile"

    log(f"Creating Payload For `{model}`")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
    )

    log(f"Recieved Response Of `{len(response.model_dump())}` Objects.")

    return response.model_dump()

def imageToText(image: str) -> str:
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    log(f"Creating Payload For `{model}`")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Your task is to respond only with the content extracted from the image provided by the user. "
                    "Format your response as a JSON object with two keys: 'user' and 'message', representing the sender and the message content respectively."
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
                            "url": f"data:image/jpeg;base64,{encode_image(image)}"
                        }
                    }
                ]
            }
        ]
    )

    log(f"Received Response With {len(response.choices)} Choices.")
    return response.choices[0].message.content