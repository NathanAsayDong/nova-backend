"""
Keeps the in-memory LLM history from growing without bound.

Every request resends the whole history, and the time to the model's first
token grows with it. Two compactions, both done in *batches* so the prompt
cache is only invalidated occasionally instead of on every turn (editing a
message deep in the history changes the cached prefix from that point on):

- Old tool results: once the tool results older than the most recent
  `keep_recent` messages add up to `clear_trigger_chars`, every one of them
  is replaced by a short placeholder in one pass.
- Message cap: once history passes `max_messages`, the oldest messages are
  dropped down to `trim_to`, cutting at a plain user message so the history
  still starts on a valid turn.

Only the in-memory history is touched. The database keeps everything.
"""

import os
from typing import Any

CLEARED_PLACEHOLDER = "[older tool result cleared to save context]"
_MIN_CLEAR_CHARS = 300


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _block_chars(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(b.get("text", "")) if isinstance(b, dict) else 0 for b in content
        )
    return 0


def _clearable_blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Result blocks in a message whose content is big enough to be worth clearing."""
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [
        block
        for block in content
        if isinstance(block, dict)
        and block.get("type") in ("tool_result", "mcp_tool_result")
        and _block_chars(block.get("content")) >= _MIN_CLEAR_CHARS
    ]


def clear_old_tool_results(
    history: list[dict[str, Any]], keep_recent: int, clear_trigger_chars: int
) -> int:
    """Replace big old tool results with a placeholder once enough pile up. Returns blocks cleared."""
    older = history[: max(0, len(history) - keep_recent)]
    blocks = [b for m in older for b in _clearable_blocks(m)]
    if sum(_block_chars(b.get("content")) for b in blocks) < clear_trigger_chars:
        return 0
    for block in blocks:
        block["content"] = CLEARED_PLACEHOLDER
    return len(blocks)


def _is_plain_user_turn(message: dict[str, Any]) -> bool:
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and not any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    )


def cap_messages(history: list[dict[str, Any]], max_messages: int, trim_to: int) -> int:
    """Drop the oldest messages down to about `trim_to` once past `max_messages`. Returns messages dropped."""
    if len(history) <= max_messages:
        return 0
    start = len(history) - trim_to
    while start < len(history) and not _is_plain_user_turn(history[start]):
        start += 1
    if start >= len(history):
        return 0
    del history[:start]
    return start


def compact_history(history: list[dict[str, Any]]) -> dict[str, int]:
    """Run both compactions with the env-tunable limits. NOVA_HISTORY_COMPACTION=0 turns it off."""
    if os.getenv("NOVA_HISTORY_COMPACTION", "1") == "0":
        return {"cleared": 0, "dropped": 0}
    max_messages = _env_int("NOVA_HISTORY_MAX_MESSAGES", 60)
    trim_to = min(_env_int("NOVA_HISTORY_TRIM_TO", 40), max_messages)
    cleared = clear_old_tool_results(
        history,
        keep_recent=_env_int("NOVA_TOOL_RESULT_KEEP_MESSAGES", 12),
        clear_trigger_chars=_env_int("NOVA_TOOL_RESULT_CLEAR_CHARS", 30000),
    )
    dropped = cap_messages(history, max_messages, trim_to)
    return {"cleared": cleared, "dropped": dropped}
