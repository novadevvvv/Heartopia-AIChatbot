from src.ai.groq import getResponse
import os

apiEnv = "heartopiaChatAPI"

apiKey = os.getenv(apiEnv)

print(apiKey[:2])

# print(getResponse("Please briefly explain the importance of fast AI inference.", "You are an assistant"))