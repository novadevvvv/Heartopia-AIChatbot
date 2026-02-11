import os
import requests
from ..log import log

"""
Website: https://github.com/novadevvvv
Dependencies: "log.py"
Path: "src/ai/"
"""

apiEnv = "heartopiaChatAPI"
apiKey = os.getenv(apiEnv)

log(f"Got API Key Starting Woith {apiKey[:2]}")

if not apiKey:
    raise RuntimeError(f"Environment variable '{apiEnv}' not set")

URL = "https://api.groq.com/openai/v1/chat/completions"

def getResponse(prompt: str, context : str) -> str:
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": f"Your Role Is `{context}`",
                "content": prompt
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {apiKey}"
    }

    response = requests.post(URL, json=payload, headers=headers)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]
