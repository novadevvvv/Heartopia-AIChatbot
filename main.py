from time import sleep as wait
from src.log import log
from src.heartopia.interfacing import click, sendChat, closeChat

import pyperclip
import pyautogui

"""
Website: https://github.com/novadevvvv
Dependencies: None
"""

log("Tab Into Heartopia!")

wait(1)

sendChat("test")

closeChat()
