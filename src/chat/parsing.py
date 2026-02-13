import json
import re
from typing import Any


VALID_SIDES = {"left", "right", "unknown"}
UI_NOISE_MESSAGES = {"baboo!"}
ROLE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def _normalize_side(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    if normalized in VALID_SIDES:
        return normalized
    return "unknown"


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_text_for_history(text: str) -> str:
    return _coerce_text(text).lower()


def _normalize_role_name(value: str) -> str:
    compact = ROLE_NAME_PATTERN.sub("_", value).strip("_")
    return compact[:64]


def _coerce_norm_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= number <= 1.0:
        return number
    return None


def _infer_side_from_geometry(message: dict[str, Any], fallback_side: str) -> str:
    # Prefer border-contact geometry over center. Long bubbles can skew centers.
    x_min = _coerce_norm_float(message.get("x_min"))
    x_max = _coerce_norm_float(message.get("x_max"))
    if x_min is not None and x_max is not None:
        left_touch = x_min
        right_touch = 1.0 - x_max
        if right_touch <= 0.12 and right_touch < left_touch:
            return "right"
        if left_touch <= 0.12 and left_touch < right_touch:
            return "left"

    x_center = _coerce_norm_float(message.get("x_center"))
    if x_center is not None:
        return "right" if x_center >= 0.58 else "left"

    return fallback_side


def _normalize_message(message: Any) -> dict[str, str] | None:
    if not isinstance(message, dict):
        return None

    text = _coerce_text(message.get("message"))
    side = _normalize_side(message.get("side"))
    side = _infer_side_from_geometry(message, side)
    raw_user = _coerce_text(message.get("user"))

    # OCR can misplace bubble text into `user` and leave `message` empty.
    if not text and raw_user and (" " in raw_user or len(raw_user) > 16):
        text = raw_user
        raw_user = "unknown"

    if not text:
        return None

    user = raw_user or ("player" if side == "left" else "ai" if side == "right" else "unknown")

    if text.lower() in UI_NOISE_MESSAGES and side == "right":
        return None

    return {
        "side": side,
        "user": user,
        "message": text,
    }


def _from_messages_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        raw_messages = []

    messages = []
    for message in raw_messages:
        normalized = _normalize_message(message)
        if normalized:
            messages.append(normalized)

    return {
        "chat_region_detected": bool(payload.get("chat_region_detected", False)),
        "messages": messages,
    }


def parse_chat_payload(raw_chat: str) -> dict[str, Any]:
    """
    Parse OCR output into normalized chat structure.

    Normalized output schema:
    {
      "chat_region_detected": bool,
      "messages": [
        {"side": "left|right|unknown", "user": str, "message": str}
      ]
    }
    """
    parsed = _load_json_with_repair(raw_chat)

    if isinstance(parsed, dict):
        if "messages" in parsed:
            return _from_messages_payload(parsed)

        # Backward compatibility: single message object
        single = _normalize_message(parsed)
        return {
            "chat_region_detected": bool(single),
            "messages": [single] if single else [],
        }

    if isinstance(parsed, list):
        normalized_messages = []
        for item in parsed:
            normalized = _normalize_message(item)
            if normalized:
                normalized_messages.append(normalized)

        return {
            "chat_region_detected": bool(normalized_messages),
            "messages": normalized_messages,
        }

    fallback_lines = [line.strip() for line in raw_chat.splitlines() if line.strip()]
    return {
        "chat_region_detected": bool(fallback_lines),
        "messages": [
            {"side": "unknown", "user": "unknown", "message": line}
            for line in fallback_lines
        ],
    }


def get_inbound_player_messages(parsed_chat: dict[str, Any]) -> list[dict[str, str]]:
    messages = parsed_chat.get("messages", [])
    if not isinstance(messages, list):
        return []

    inbound = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("side") != "left":
            continue
        text = _coerce_text(message.get("message"))
        if not text:
            continue
        inbound.append(
            {
                "side": "left",
                "user": _coerce_text(message.get("user")) or "player",
                "message": text,
            }
        )
    return inbound


def get_messages_not_from_ai_history(
    parsed_chat: dict[str, Any], ai_message_history: set[str]
) -> list[dict[str, str]]:
    messages = parsed_chat.get("messages", [])
    if not isinstance(messages, list):
        return []

    inbound = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        text = _coerce_text(message.get("message"))
        if not text:
            continue

        if normalize_text_for_history(text) in ai_message_history:
            continue

        inbound.append(
            {
                "side": _normalize_side(message.get("side")),
                "user": _coerce_text(message.get("user")) or "player",
                "message": text,
            }
        )

    return inbound


def build_llm_role_messages(parsed_chat: dict[str, Any]) -> list[dict[str, str]]:
    messages = parsed_chat.get("messages", [])
    if not isinstance(messages, list):
        return []

    role_messages: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue

        text = _coerce_text(message.get("message"))
        if not text:
            continue

        side = _normalize_side(message.get("side"))
        role = "assistant" if side == "right" else "user"
        role_message: dict[str, str] = {
            "role": role,
            "content": text,
        }

        if role == "user":
            user_name = _normalize_role_name(_coerce_text(message.get("user")))
            if user_name and user_name not in {"player", "unknown"}:
                role_message["name"] = user_name

        role_messages.append(role_message)

    return role_messages


def _load_json_with_repair(raw_chat: str) -> Any:
    try:
        return json.loads(raw_chat)
    except json.JSONDecodeError:
        pass

    # Repair common model issue: trailing commas before } or ].
    repaired = re.sub(r",\s*([}\]])", r"\1", raw_chat)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None
