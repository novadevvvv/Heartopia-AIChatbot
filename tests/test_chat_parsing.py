import unittest

from src.chat.parsing import (
    build_llm_role_messages,
    get_inbound_player_messages,
    get_messages_not_from_ai_history,
    normalize_text_for_history,
    parse_chat_payload,
)


class TestChatParsing(unittest.TestCase):
    def test_parses_strict_schema(self):
        raw = (
            '{"chat_region_detected": true, "messages": ['
            '{"side":"left","user":"Alex","message":"hey there"},'
            '{"side":"right","user":"AI","message":"yo"}]}'
        )

        parsed = parse_chat_payload(raw)

        self.assertTrue(parsed["chat_region_detected"])
        self.assertEqual(len(parsed["messages"]), 2)
        self.assertEqual(parsed["messages"][0]["side"], "left")
        self.assertEqual(parsed["messages"][1]["side"], "right")

    def test_backward_compatible_single_message_dict(self):
        raw = '{"user":"player","message":"hello"}'
        parsed = parse_chat_payload(raw)

        self.assertTrue(parsed["chat_region_detected"])
        self.assertEqual(len(parsed["messages"]), 1)
        self.assertEqual(parsed["messages"][0]["message"], "hello")
        self.assertEqual(parsed["messages"][0]["side"], "unknown")

    def test_fallback_text_lines(self):
        raw = "line one\n\nline two"
        parsed = parse_chat_payload(raw)

        self.assertTrue(parsed["chat_region_detected"])
        self.assertEqual(
            parsed["messages"],
            [
                {"side": "unknown", "user": "unknown", "message": "line one"},
                {"side": "unknown", "user": "unknown", "message": "line two"},
            ],
        )

    def test_inbound_filters_left_only(self):
        parsed = {
            "chat_region_detected": True,
            "messages": [
                {"side": "left", "user": "A", "message": "hi"},
                {"side": "right", "user": "B", "message": "yo"},
                {"side": "unknown", "user": "C", "message": "??"},
            ],
        }

        inbound = get_inbound_player_messages(parsed)
        self.assertEqual(inbound, [{"side": "left", "user": "A", "message": "hi"}])

    def test_output_schema_shape(self):
        parsed = parse_chat_payload('{"chat_region_detected": false, "messages": []}')

        self.assertIn("chat_region_detected", parsed)
        self.assertIn("messages", parsed)
        self.assertIsInstance(parsed["chat_region_detected"], bool)
        self.assertIsInstance(parsed["messages"], list)

    def test_side_prefers_x_center_when_present(self):
        raw = (
            '{"chat_region_detected": true, "messages": ['
            '{"side":"left","x_center":0.88,"user":"unknown","message":"MEOW"},'
            '{"side":"right","x_center":0.20,"user":"Irin","message":"hello"}]}'
        )
        parsed = parse_chat_payload(raw)
        self.assertEqual(parsed["messages"][0]["side"], "right")
        self.assertEqual(parsed["messages"][1]["side"], "left")

    def test_side_prefers_border_touch_over_center(self):
        raw = (
            '{"chat_region_detected": true, "messages": ['
            '{"side":"left","x_min":0.62,"x_max":0.99,"x_center":0.40,"user":"unknown","message":"long right bubble"},'
            '{"side":"right","x_min":0.01,"x_max":0.38,"x_center":0.70,"user":"unknown","message":"left bubble"}]}'
        )
        parsed = parse_chat_payload(raw)
        self.assertEqual(parsed["messages"][0]["side"], "right")
        self.assertEqual(parsed["messages"][1]["side"], "left")

    def test_filters_messages_already_sent_by_ai(self):
        parsed = {
            "chat_region_detected": True,
            "messages": [
                {"side": "right", "user": "unknown", "message": "MEOW"},
                {"side": "left", "user": "Irin", "message": "hello"},
                {"side": "unknown", "user": "unknown", "message": "hello there"},
            ],
        }
        ai_history = {normalize_text_for_history("meow")}

        inbound = get_messages_not_from_ai_history(parsed, ai_history)

        self.assertEqual(
            inbound,
            [
                {"side": "left", "user": "Irin", "message": "hello"},
                {"side": "unknown", "user": "unknown", "message": "hello there"},
            ],
        )

    def test_filters_case_insensitive_ai_history(self):
        parsed = {
            "chat_region_detected": True,
            "messages": [
                {"side": "right", "user": "unknown", "message": "mEoW"},
                {"side": "left", "user": "A", "message": "Yo"},
            ],
        }
        ai_history = {normalize_text_for_history("MEOW")}

        inbound = get_messages_not_from_ai_history(parsed, ai_history)
        self.assertEqual(inbound, [{"side": "left", "user": "A", "message": "Yo"}])

    def test_repairs_trailing_comma_json(self):
        raw = (
            '{"chat_region_detected": true, "messages": ['
            '{"side":"left","user":"Irin","message":"What data is it getting to move?"},'
            '{"side":"left","user":"Irin","message":"At what frequency?"},]}'
        )
        parsed = parse_chat_payload(raw)
        self.assertEqual(len(parsed["messages"]), 2)
        self.assertEqual(parsed["messages"][0]["message"], "What data is it getting to move?")

    def test_salvages_text_from_user_when_message_empty(self):
        raw = (
            '{"chat_region_detected": true, "messages": ['
            '{"side":"left","user":"the cheese grater tomato","message":""}]}'
        )
        parsed = parse_chat_payload(raw)
        self.assertEqual(len(parsed["messages"]), 1)
        self.assertEqual(parsed["messages"][0]["message"], "the cheese grater tomato")
        self.assertEqual(parsed["messages"][0]["user"], "unknown")

    def test_builds_role_messages_left_user_right_assistant(self):
        parsed = {
            "chat_region_detected": True,
            "messages": [
                {"side": "left", "user": "Irin", "message": "hello"},
                {"side": "right", "user": "unknown", "message": "yo"},
            ],
        }
        role_messages = build_llm_role_messages(parsed)
        self.assertEqual(
            role_messages,
            [
                {"role": "user", "name": "Irin", "content": "hello"},
                {"role": "assistant", "content": "yo"},
            ],
        )

    def test_builds_role_messages_with_sanitized_user_name(self):
        parsed = {
            "chat_region_detected": True,
            "messages": [
                {"side": "left", "user": "A B!", "message": "sup"},
            ],
        }
        role_messages = build_llm_role_messages(parsed)
        self.assertEqual(
            role_messages,
            [{"role": "user", "name": "A_B", "content": "sup"}],
        )


if __name__ == "__main__":
    unittest.main()
