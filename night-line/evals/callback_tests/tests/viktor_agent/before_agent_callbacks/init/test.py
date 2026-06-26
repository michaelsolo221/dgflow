"""Callback tests for before_agent_callback (init) — Viktor."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from conftest import MockCallbackContext

_agents_dir = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "agents"
    / "viktor_agent"
    / "before_agent_callbacks"
    / "init"
)
_spec = importlib.util.spec_from_file_location("viktor_before_agent_init", str(_agents_dir / "python_code.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
before_agent_callback = _mod.before_agent_callback




def test_turn_guard_fires_on_second_invocation():
    """Turn guard: returns None immediately when _initialized == 'true'."""
    ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "true"})
    assert before_agent_callback(ctx) is None


@patch("google.cloud.firestore.Client")
def test_firestore_load_populates_state(mock_firestore_client):
    """On first call with existing Firestore doc, state is populated."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "caller_id": "+15551234567",
        "call_count": 3,
        "facts": {"name": "Alice"},
        "recent_turns": [{"role": "user", "text": "Hi"}],
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    mock_firestore_client.return_value = mock_db

    ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
    result = before_agent_callback(ctx)

    assert result is None
    assert ctx.state["_initialized"] == "true"
    assert ctx.state["persona_id"] == "viktor"
    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 4
    assert profile["facts"]["name"] == "Alice"


@patch("google.cloud.firestore.Client")
def test_call_count_increments_on_repeat_caller(mock_firestore_client):
    """call_count increments for an existing caller."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"caller_id": "+15551234567", "call_count": 7, "facts": {}, "recent_turns": []}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    mock_firestore_client.return_value = mock_db

    ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
    before_agent_callback(ctx)

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 8


@patch("google.cloud.firestore.Client")
def test_exception_falls_back_to_safe_default(mock_firestore_client):
    """When Firestore throws, a safe default profile is set."""
    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
    result = before_agent_callback(ctx)

    assert result is None
    assert ctx.state["_initialized"] == "true"
    assert ctx.state["persona_id"] == "viktor"
    profile = json.loads(ctx.state["caller_profile"])
    assert profile["caller_id"] == "+15551234567"
    assert profile["call_count"] == 1
    assert profile["facts"] == {}
