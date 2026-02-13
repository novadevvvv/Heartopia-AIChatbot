import json
import unittest

from PIL import Image, ImageDraw

from src.heartopia.side_inference import correct_message_sides


def _mk_test_image() -> Image.Image:
    img = Image.new("RGB", (200, 120), (236, 231, 226))
    d = ImageDraw.Draw(img)
    # Right bubble edge markers near y~25.
    d.rectangle((192, 15, 199, 35), fill=(30, 30, 30))
    # Left bubble edge markers near y~85.
    d.rectangle((0, 75, 8, 95), fill=(30, 30, 30))
    return img


class TestSideInference(unittest.TestCase):
    def test_corrects_sides_using_edge_probes(self):
        payload = {
            "chat_region_detected": True,
            "messages": [
                {"side": "left", "y_center": 0.2, "message": "r1"},
                {"side": "right", "y_center": 0.7, "message": "l1"},
            ],
        }
        raw = json.dumps(payload)
        corrected = json.loads(correct_message_sides(raw, _mk_test_image()))

        self.assertEqual(corrected["messages"][0]["side"], "right")
        self.assertEqual(corrected["messages"][1]["side"], "left")

    def test_keeps_payload_when_invalid_json(self):
        raw = "not-json"
        self.assertEqual(correct_message_sides(raw, _mk_test_image()), raw)

    def test_prefers_split_threshold_geometry(self):
        payload = {
            "chat_region_detected": True,
            "messages": [
                {"side": "unknown", "x_min": 0.60, "x_max": 0.95, "x_center": 0.77, "message": "r"},
                {"side": "unknown", "x_min": 0.02, "x_max": 0.45, "x_center": 0.23, "message": "l"},
            ],
        }
        raw = json.dumps(payload)
        corrected = json.loads(
            correct_message_sides(
                raw,
                _mk_test_image(),
                classifier_hints={"split_norm": 0.52, "left_lane_norm": 0.2, "right_lane_norm": 0.8},
            )
        )
        self.assertEqual(corrected["messages"][0]["side"], "right")
        self.assertEqual(corrected["messages"][1]["side"], "left")

    def test_lane_evidence_can_override_split(self):
        img = Image.new("RGB", (200, 120), (236, 231, 226))
        d = ImageDraw.Draw(img)
        # Strong left-lane signal at y~20.
        d.rectangle((34, 10, 46, 30), fill=(20, 20, 20))
        # Weak right-lane signal at same band.
        d.rectangle((160, 18, 164, 22), fill=(20, 20, 20))

        payload = {
            "chat_region_detected": True,
            "messages": [
                {"side": "unknown", "x_min": 0.60, "x_max": 0.95, "x_center": 0.77, "y_center": 0.17, "message": "m"},
            ],
        }
        raw = json.dumps(payload)
        corrected = json.loads(
            correct_message_sides(
                raw,
                img,
                classifier_hints={"split_norm": 0.5, "left_lane_norm": 0.2, "right_lane_norm": 0.8},
            )
        )
        self.assertEqual(corrected["messages"][0]["side"], "left")


if __name__ == "__main__":
    unittest.main()
