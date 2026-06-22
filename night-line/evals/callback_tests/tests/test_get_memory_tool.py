"""Callback unit tests for get_memory tool — NO-GO gate for graceful degradation.

These tests explicitly inject Firestore failures and assert the tool's fallback
message is persona-safe: no 'error', 'failed', 'system', or 'try again' language
that would break character if surfaced by the persona.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Point at the real tool implementation
_TOOL_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "cxas_app" / "NightLine" / "tools" / "get_memory" / "python_function"
)
sys.path.insert(0, str(_TOOL_DIR))


class MockCallbackContext:
    def __init__(self, state=None):
        self.state = dict(state or {})


def _get_get_memory():
    import importlib
    sys.modules.pop("python_code", None)
    mod = importlib.import_module("python_code")
    return mod.get_memory


_BANNED_WORDS = {"error", "failed", "system", "try again"}


@patch("google.cloud.firestore.Client")
def test_firestore_error_returns_agent_action_not_raises(mock_firestore_client):
    """On Firestore failure get_memory must return agent_action, never raise."""
    get_memory = _get_get_memory()
    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({"caller_id": "+15551234567"})
    result = get_memory(ctx)

    assert "agent_action" in result, "Must return agent_action key on error, not raise"
    assert "caller_profile" not in result, "Must NOT return caller_profile on error"


@patch("google.cloud.firestore.Client")
def test_firestore_error_fallback_message_is_persona_safe(mock_firestore_client):
    """The fallback agent_action message must contain no error/system language
    that would break the persona if the LLM echoes it back to the caller.

    NO-GO gate: if this test fails, graceful degradation is broken.
    """
    get_memory = _get_get_memory()
    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({"caller_id": "+15551234567"})
    result = get_memory(ctx)

    message = result.get("agent_action", "").lower()
    found_banned = [word for word in _BANNED_WORDS if word in message]
    assert not found_banned, (
        f"agent_action message contains banned word(s) {found_banned!r} "
        f"that would break persona character: {message!r}"
    )


@patch("google.cloud.firestore.Client")
def test_firestore_doc_get_raises_returns_agent_action(mock_firestore_client):
    """Error during .get() (not just Client init) also falls back gracefully."""
    get_memory = _get_get_memory()
    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.get.side_effect = RuntimeError(
        "Network timeout"
    )
    mock_firestore_client.return_value = mock_db

    ctx = MockCallbackContext({"caller_id": "+15551234567"})
    result = get_memory(ctx)

    assert "agent_action" in result
    message = result["agent_action"].lower()
    found_banned = [word for word in _BANNED_WORDS if word in message]
    assert not found_banned, (
        f"agent_action message contains banned word(s) {found_banned!r}: {message!r}"
    )
