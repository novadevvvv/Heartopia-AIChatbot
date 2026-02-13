import os
import unittest

from src.env_loader import load_env_file

load_env_file()


@unittest.skipUnless(
    os.getenv("RUN_CHAT_TESTS") == "1",
    "Set RUN_CHAT_TESTS=1 to run Groq chat integration tests.",
)
class TestGroqChatIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.getenv("heartopiaChatAPI"):
            raise unittest.SkipTest("heartopiaChatAPI environment variable is not set.")

        # Import late to avoid module side effects when tests are skipped.
        try:
            from src.ai.groq import getResponse
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"Missing dependency: {exc}") from exc

        cls.get_response = staticmethod(getResponse)

    def _assert_chat_response_shape(self, response: dict) -> None:
        self.assertIsInstance(response, dict)
        self.assertIn("choices", response)
        self.assertIsInstance(response["choices"], list)
        self.assertGreater(len(response["choices"]), 0)
        first = response["choices"][0]
        self.assertIsInstance(first, dict)
        self.assertIn("message", first)
        self.assertIsInstance(first["message"], dict)
        self.assertIn("content", first["message"])
        self.assertIsInstance(first["message"]["content"], str)
        self.assertTrue(first["message"]["content"].strip())

    def test_get_response_basic_live(self):
        response = self.get_response(
            prompt="Say hello in one short sentence.",
            context="You are a friendly in-game chatbot.",
        )
        self._assert_chat_response_shape(response)

    def test_get_response_with_role_history_live(self):
        response = self.get_response(
            prompt="unused",
            context="You are a friendly in-game chatbot.",
            conversation_messages=[
                {"role": "user", "name": "Irin", "content": "Hey!"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "name": "Irin", "content": "How are you?"},
            ],
        )
        self._assert_chat_response_shape(response)


if __name__ == "__main__":
    unittest.main()
