import pyautogui
from time import sleep as wait
import random
from ..log import log
import pyperclip

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

    click((1388, 822))

    pyperclip.copy(message)
    pyautogui.hotkey("ctrl", "v")

    click((1782, 823))