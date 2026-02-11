import json
import os
import pyautogui
from time import sleep as wait
import random
import pyperclip
from PIL import ImageOps, ImageEnhance
from ..log import log
from ..ai.groq import imageToText

CONFIG_PATH = "config.json"
chatOpen: bool = False

# Default positions and areas we need
required_positions = {
    "chat_button": None,
    "chat_bubble": None,
    "text_box": None,
    "send_button": None,
    "chat_area": None  # (x, y, width, height)
}

def load_or_prompt_positions():
    """Load positions from config.json or prompt user to set them."""
    # Load existing config if it exists
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            for key in required_positions:
                if key in data:
                    required_positions[key] = tuple(data[key])

    # Prompt for any missing positions
    for key, val in required_positions.items():
        if val is None:
            if key == "chat_area":
                log(
                    "Please move your mouse to the TOP-LEFT of the chat area, press Enter, "
                    "then move to the BOTTOM-RIGHT of the chat area and press Enter again..."
                )
                input("Move to top-left and press Enter...")
                top_left = pyautogui.position()
                input("Move to bottom-right and press Enter...")
                bottom_right = pyautogui.position()
                x = top_left.x
                y = top_left.y
                width = bottom_right.x - top_left.x
                height = bottom_right.y - top_left.y
                required_positions[key] = (x, y, width, height)
            else:
                log(f"Please move your mouse to the {key.replace('_', ' ')} and press Enter...")
                input()
                pos = pyautogui.position()
                required_positions[key] = (pos.x, pos.y)
            log(f"{key} set to {required_positions[key]}")

    # Save back to config.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(required_positions, f, indent=4)

def click(position: tuple[int, int], duration: float = 0.01) -> None:
    log(f"Clicking at {position}")
    pyautogui.moveTo(position[0], position[1], duration=0)
    wait(0.01)
    pyautogui.moveRel(random.randint(1,2), random.randint(1,2), duration=0)
    wait(0.05)
    pyautogui.mouseDown()
    wait(duration)
    pyautogui.mouseUp()

def openChat() -> None:
    global chatOpen
    if chatOpen:
        return
    click(required_positions["chat_button"])
    click(required_positions["chat_bubble"])
    chatOpen = True

def closeChat() -> None:
    global chatOpen
    if not chatOpen:
        return
    click(required_positions["chat_bubble"])
    chatOpen = False

def sendChat(message: str) -> None:
    global chatOpen
    if not chatOpen:
        openChat()

    def sendPacket(packet: str):
        click(required_positions["text_box"])
        pyperclip.copy(packet)
        pyautogui.hotkey("ctrl", "v")
        click(required_positions["send_button"])

    messages = [message[i:i+40] for i in range(0, len(message), 40)]
    for packet in messages:
        sendPacket(packet)

def getChat() -> list:
    global chatOpen
    if not chatOpen:
        openChat()
    wait(0.5)
    x, y, width, height = required_positions["chat_area"]
    screenshot = pyautogui.screenshot("chat.png", region=(x, y, width, height))
    return imageToText(screenshot)

# Initialize positions on import
load_or_prompt_positions()
