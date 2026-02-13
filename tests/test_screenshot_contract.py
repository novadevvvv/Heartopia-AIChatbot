import json
import os
import unittest
from pathlib import Path

from src.env_loader import load_env_file
from src.chat.parsing import parse_chat_payload

load_env_file()

FIXTURE_DIR = Path("tests/fixtures/screenshots")
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"


def _message_matches(actual: dict, expected: dict) -> bool:
    expected_side = expected.get("side")
    if expected_side and actual.get("side") != expected_side:
        return False

    expected_contains = expected.get("message_contains")
    if expected_contains:
        actual_text = (actual.get("message") or "").lower()
        if expected_contains.lower() not in actual_text:
            return False

    return True


def _pretty(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


@unittest.skipUnless(
    os.getenv("RUN_VISION_TESTS") == "1",
    "Set RUN_VISION_TESTS=1 to run screenshot integration tests.",
)
class TestScreenshotContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST_PATH.exists():
            raise unittest.SkipTest("No tests/fixtures/screenshots/manifest.json found.")
        if not os.getenv("heartopiaChatAPI"):
            raise unittest.SkipTest("heartopiaChatAPI environment variable is not set.")

        # Import late to avoid module side effects when tests are skipped.
        try:
            from src.ai.groq import imageToText
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Missing dependency: {exc}") from exc

        cls.image_to_text = staticmethod(imageToText)
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_cases(self):
        cases = self.manifest.get("cases", [])
        if not cases:
            self.skipTest("Manifest contains no test cases.")

        for case in cases:
            with self.subTest(case=case.get("name", "unnamed")):
                image_path = FIXTURE_DIR / case["image"]
                self.assertTrue(image_path.exists(), f"Missing image: {image_path}")

                raw = self.image_to_text(str(image_path))
                parsed = parse_chat_payload(raw)

                expected = case.get("expected", {})
                failure_header = (
                    f"Case: {case.get('name', 'unnamed')}\n"
                    f"Image: {image_path}\n"
                    f"Expected:\n{_pretty(expected)}\n"
                    f"Raw model output:\n{raw}\n"
                    f"Parsed output:\n{_pretty(parsed)}\n"
                )
                self.assertEqual(
                    parsed["chat_region_detected"],
                    expected.get("chat_region_detected", True),
                    msg=(
                        "chat_region_detected mismatch.\n"
                        f"{failure_header}"
                    ),
                )

                expected_messages = expected.get("messages", [])
                exact_message_count = expected.get("exact_message_count")
                if exact_message_count is not None:
                    self.assertEqual(
                        len(parsed["messages"]),
                        exact_message_count,
                        msg=(
                            "Model returned unexpected message count.\n"
                            f"{failure_header}"
                        ),
                    )
                self.assertGreaterEqual(
                    len(parsed["messages"]),
                    len(expected_messages),
                    msg=(
                        "Model returned fewer messages than expected contract.\n"
                        f"{failure_header}"
                    ),
                )

                for idx, expected_message in enumerate(expected_messages):
                    self.assertTrue(
                        _message_matches(parsed["messages"][idx], expected_message),
                        msg=(
                            f"Mismatch at message index {idx}.\n"
                            f"Expected message:\n{_pretty(expected_message)}\n"
                            f"Actual message:\n{_pretty(parsed['messages'][idx])}\n"
                            f"{failure_header}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
