from src.harness.history_compaction import (
    CLEARED_PLACEHOLDER,
    cap_messages,
    clear_old_tool_results,
    compact_history,
)


def _turn(i, result_chars=1000):
    return [
        {"role": "user", "content": f"q{i}"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": "x", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "r" * result_chars}]},
        {"role": "assistant", "content": f"a{i}"},
    ]


def _history(n, result_chars=1000):
    return [m for i in range(n) for m in _turn(i, result_chars)]


def test_clear_waits_for_trigger():
    h = _history(3)
    assert clear_old_tool_results(h, keep_recent=4, clear_trigger_chars=10_000) == 0
    assert h[2]["content"][0]["content"] == "r" * 1000


def test_clear_old_only_and_batches():
    h = _history(10)
    cleared = clear_old_tool_results(h, keep_recent=8, clear_trigger_chars=5_000)
    assert cleared == 8
    assert h[2]["content"][0]["content"] == CLEARED_PLACEHOLDER
    assert h[-2]["content"][0]["content"] == "r" * 1000  # recent kept


def test_small_results_untouched():
    h = _history(10, result_chars=50)
    assert clear_old_tool_results(h, keep_recent=4, clear_trigger_chars=1) == 0


def test_cap_noop_under_limit():
    h = _history(5)
    assert cap_messages(h, max_messages=60, trim_to=40) == 0


def test_cap_cuts_on_plain_user_turn():
    h = _history(20)
    dropped = cap_messages(h, max_messages=60, trim_to=42)
    assert dropped > 0
    assert h[0]["role"] == "user" and isinstance(h[0]["content"], str)
    assert len(h) <= 44


def test_compact_history_kill_switch(monkeypatch):
    monkeypatch.setenv("NOVA_HISTORY_COMPACTION", "0")
    h = _history(30)
    n = len(h)
    assert compact_history(h) == {"cleared": 0, "dropped": 0}
    assert len(h) == n
