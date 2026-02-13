import unittest
from pathlib import Path

from PIL import Image

from src.heartopia.chat_preprocess import crop_chat_message_list


FIXTURE_DIR = Path("tests/fixtures/screenshots")


def _teal_ratio(image: Image.Image) -> float:
    total = image.width * image.height
    if total == 0:
        return 0.0
    teal = 0
    for r, g, b in image.getdata():
        if g > 150 and b > 140 and r < 120:
            teal += 1
    return teal / total


class TestChatPreprocess(unittest.TestCase):
    def test_crop_returns_stable_message_list_region(self):
        screenshots = sorted(FIXTURE_DIR.glob("*.png"))
        self.assertGreater(len(screenshots), 0, "No screenshot fixtures found.")

        for screenshot in screenshots:
            with self.subTest(image=screenshot.name):
                full = Image.open(screenshot).convert("RGB")
                cropped = crop_chat_message_list(full)

                self.assertLess(cropped.width, full.width)
                self.assertLess(cropped.height, full.height)
                self.assertGreater(cropped.width, 300)
                self.assertGreater(cropped.height, 200)

    def test_crop_excludes_composer_send_button_area(self):
        screenshots = sorted(FIXTURE_DIR.glob("*.png"))
        self.assertGreater(len(screenshots), 0, "No screenshot fixtures found.")

        for screenshot in screenshots:
            with self.subTest(image=screenshot.name):
                full = Image.open(screenshot).convert("RGB")
                cropped = crop_chat_message_list(full)

                self.assertLessEqual(_teal_ratio(cropped), 0.002)


if __name__ == "__main__":
    unittest.main()
