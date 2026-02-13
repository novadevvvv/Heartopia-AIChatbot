import json
from typing import Any

from PIL import Image


def _coerce_norm(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= number <= 1.0:
        return number
    return None


def _is_dark(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return r < 120 and g < 120 and b < 120


def _edge_scores(image: Image.Image, y_center_norm: float) -> tuple[int, int]:
    img = image.convert("RGB")
    width, height = img.size
    px = img.load()

    y_center = int(y_center_norm * (height - 1))
    y0 = max(0, y_center - 10)
    y1 = min(height - 1, y_center + 10)

    left_score = 0
    right_score = 0

    left_x_end = min(width - 1, int(width * 0.07))
    right_x_start = max(0, int(width * 0.93))

    for y in range(y0, y1 + 1):
        for x in range(0, left_x_end + 1):
            if _is_dark(px[x, y]):
                left_score += 1
        for x in range(right_x_start, width):
            if _is_dark(px[x, y]):
                right_score += 1

    return left_score, right_score


def _lane_scores(image: Image.Image, y_center_norm: float, left_lane_norm: float, right_lane_norm: float) -> tuple[int, int]:
    img = image.convert("RGB")
    width, height = img.size
    px = img.load()

    y_center = int(y_center_norm * (height - 1))
    y0 = max(0, y_center - 10)
    y1 = min(height - 1, y_center + 10)

    left_x = max(0, min(width - 1, int(left_lane_norm * (width - 1))))
    right_x = max(0, min(width - 1, int(right_lane_norm * (width - 1))))

    left_score = 0
    right_score = 0
    x_band = 6
    for y in range(y0, y1 + 1):
        for x in range(max(0, left_x - x_band), min(width, left_x + x_band + 1)):
            if _is_dark(px[x, y]):
                left_score += 1
        for x in range(max(0, right_x - x_band), min(width, right_x + x_band + 1)):
            if _is_dark(px[x, y]):
                right_score += 1

    return left_score, right_score


def _normalize_side(side: Any) -> str:
    if isinstance(side, str):
        lowered = side.strip().lower()
        if lowered in {"left", "right", "unknown"}:
            return lowered
    return "unknown"


def _coerce_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []
    return [m for m in messages if isinstance(m, dict)]


def _classify_with_split(message: dict[str, Any], split_norm: float) -> str | None:
    x_min = _coerce_norm(message.get("x_min"))
    x_max = _coerce_norm(message.get("x_max"))
    x_center = _coerce_norm(message.get("x_center"))

    if x_min is not None and x_max is not None:
        if x_max <= split_norm:
            return "left"
        if x_min >= split_norm:
            return "right"
        # If bubble spans split, choose side with larger span from split.
        left_span = max(0.0, split_norm - x_min)
        right_span = max(0.0, x_max - split_norm)
        return "right" if right_span >= left_span else "left"

    if x_center is not None:
        return "right" if x_center >= split_norm else "left"

    return None


def correct_message_sides(
    raw_payload: str,
    cropped_image: Image.Image,
    classifier_hints: dict[str, float] | None = None,
) -> str:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return raw_payload

    if not isinstance(payload, dict):
        return raw_payload

    messages = _coerce_messages(payload)
    if not messages:
        return raw_payload

    corrected = []
    for message in messages:
        side = _normalize_side(message.get("side"))
        hints = classifier_hints or {}

        split_norm = _coerce_norm(hints.get("split_norm"))
        split_side = None
        if split_norm is not None:
            split_side = _classify_with_split(message, split_norm)
        if split_side:
            side = split_side

        y_center = _coerce_norm(message.get("y_center"))
        if y_center is not None:
            left_lane_norm = _coerce_norm(hints.get("left_lane_norm"))
            right_lane_norm = _coerce_norm(hints.get("right_lane_norm"))
            if left_lane_norm is not None and right_lane_norm is not None:
                left_score, right_score = _lane_scores(cropped_image, y_center, left_lane_norm, right_lane_norm)
            else:
                left_score, right_score = _edge_scores(cropped_image, y_center)

            # Strong visual evidence near lane anchors can override unreliable model geometry.
            if right_score > left_score * 1.25 and right_score > 12:
                side = "right"
            elif left_score > right_score * 1.25 and left_score > 12:
                side = "left"

        next_message = dict(message)
        next_message["side"] = side
        corrected.append(next_message)

    next_payload = dict(payload)
    next_payload["messages"] = corrected
    return json.dumps(next_payload, ensure_ascii=False)
