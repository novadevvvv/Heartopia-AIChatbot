import pyautogui
from time import sleep as wait
import random
from ..log import log
import pyperclip
import pytesseract
import re
from PIL import ImageOps, ImageEnhance
from ..ai.groq import imageToText

"""
Website: https://github.com/novadevvvv
Dependencies: "log.py"
Path: "src/heartopia/"
"""

chatOpen: bool = False


def click(position: tuple[int, int], duration: float = 0.01) -> None:
    log(f"Attempting to click at {position}")

    pyautogui.moveTo(position[0], position[1], duration=0)
    wait(0.01)

    # Slight offset to allow repeated clicks in same location
    pyautogui.moveRel(random.randint(1, 2), random.randint(1, 2), duration=0)

    wait(0.05)
    pyautogui.mouseDown()
    wait(duration)
    pyautogui.mouseUp()


def openChat() -> None:
    global chatOpen

    if chatOpen:
        return

    click((123, 1021))
    click((960, 399))
    chatOpen = True


def closeChat() -> None:
    global chatOpen

    if not chatOpen:
        return

    click((960, 399))
    chatOpen = False


def sendChat(message: str) -> None:
    global chatOpen

    if not chatOpen:
        openChat()

    def sendPacket(packet: str):
        click((1388, 822))
        pyperclip.copy(packet)
        pyautogui.hotkey("ctrl", "v")
        click((1782, 823))

    # Split into chunks of 40 characters
    messages = [message[i:i+40] for i in range(0, len(message), 40)]

    for packet in messages:
        sendPacket(packet)


def getChat() -> list:

    global chatOpen

    if not chatOpen:
        openChat()
    
    wait(0.5)

    screenshot = pyautogui.screenshot("chat.png",region=(1295, 370, 286, 421))

    response = imageToText(screenshot)

    return response
