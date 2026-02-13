import json
from pathlib import Path
from typing import Any

from PIL import Image


ANCHORS_PATH = Path("tools/anchor_editor/anchors.json")


def _load_image(image: str | Image.Image) -> Image.Image:
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, str):
        return Image.open(image)
    raise TypeError("image must be a file path or PIL Image")


def _clamp_rect(x: int, y: int, width: int, height: int, max_w: int, max_h: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(x, max_w - 2))
    y1 = max(0, min(y, max_h - 2))
    x2 = max(x1 + 1, min(x + width, max_w))
    y2 = max(y1 + 1, min(y + height, max_h))
    return x1, y1, x2, y2


def _load_profiles(path: Path = ANCHORS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    return profiles


def _get_profile_for_resolution(width: int, height: int, path: Path = ANCHORS_PATH) -> dict[str, Any] | None:
    key = f"{width}x{height}"
    profile = _load_profiles(path).get(key)
    if isinstance(profile, dict):
        return profile
    return None


def _crop_from_profile(source: Image.Image, profile: dict[str, Any]) -> tuple[Image.Image, dict[str, float] | None]:
    width, height = source.size
    msg_list = profile.get("message_list", {})
    if not isinstance(msg_list, dict):
        raise ValueError("Invalid profile: missing message_list")

    x = int(msg_list.get("x", 0))
    y = int(msg_list.get("y", 0))
    w = int(msg_list.get("width", 0))
    h = int(msg_list.get("height", 0))
    if w <= 1 or h <= 1:
        raise ValueError("Invalid profile: empty message_list dimensions")

    x1, y1, x2, y2 = _clamp_rect(x, y, w, h, width, height)
    cropped = source.crop((x1, y1, x2, y2))

    lanes = profile.get("lanes", {})
    classifier = profile.get("classifier", {})
    if not isinstance(lanes, dict):
        return cropped, None
    if not isinstance(classifier, dict):
        classifier = {}

    list_width = max(1, x2 - x1)
    left_lane_x = int(lanes.get("left_x", x1))
    right_lane_x = int(lanes.get("right_x", x2))
    left_norm = max(0.0, min(1.0, (left_lane_x - x1) / list_width))
    right_norm = max(0.0, min(1.0, (right_lane_x - x1) / list_width))

    split_x = int(classifier.get("split_x", (left_lane_x + right_lane_x) // 2))
    split_norm = max(0.0, min(1.0, (split_x - x1) / list_width))

    return cropped, {
        "left_lane_norm": left_norm,
        "right_lane_norm": right_norm,
        "split_norm": split_norm,
    }


def _crop_with_fallback(source: Image.Image) -> tuple[Image.Image, dict[str, float] | None]:
    width, height = source.size

    # Right-side chat panel bounds in normalized full-screen coordinates.
    panel_left = int(width * 0.67)
    panel_top = int(height * 0.21)
    panel_right = int(width * 0.97)
    panel_bottom = int(height * 0.85)

    # Safety clamps.
    panel_left = max(0, min(panel_left, width - 2))
    panel_top = max(0, min(panel_top, height - 2))
    panel_right = max(panel_left + 1, min(panel_right, width))
    panel_bottom = max(panel_top + 1, min(panel_bottom, height))

    panel = source.crop((panel_left, panel_top, panel_right, panel_bottom))
    panel_width, panel_height = panel.size

    # Message list area within panel.
    # Excludes top tab/toggle section and bottom message composer.
    list_left = int(panel_width * 0.03)
    list_top = int(panel_height * 0.16)
    list_right = int(panel_width * 0.99)
    list_bottom = int(panel_height * 0.80)

    list_left = max(0, min(list_left, panel_width - 2))
    list_top = max(0, min(list_top, panel_height - 2))
    list_right = max(list_left + 1, min(list_right, panel_width))
    list_bottom = max(list_top + 1, min(list_bottom, panel_height))

    cropped = panel.crop((list_left, list_top, list_right, list_bottom))
    # Approximate lane centers in fallback space.
    return cropped, {
        "left_lane_norm": 0.20,
        "right_lane_norm": 0.83,
        "split_norm": 0.515,
    }


def prepare_chat_message_list(
    image: str | Image.Image, anchors_path: Path = ANCHORS_PATH
) -> tuple[Image.Image, dict[str, float] | None]:
    source = _load_image(image).convert("RGB")
    width, height = source.size
    profile = _get_profile_for_resolution(width, height, path=anchors_path)
    if profile:
        try:
            return _crop_from_profile(source, profile)
        except Exception:
            return _crop_with_fallback(source)
    return _crop_with_fallback(source)


def crop_chat_message_list(image: str | Image.Image) -> Image.Image:
    """
    Backward-compatible wrapper returning only cropped image.
    """
    cropped, _ = prepare_chat_message_list(image)
    return cropped
