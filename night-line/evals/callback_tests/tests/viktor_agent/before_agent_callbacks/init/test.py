"""Callback tests for before_agent_callback (init) — Viktor."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the agents callback source dir to import path
_agents_dir = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "agents" / "viktor_agent" / "before_agent_callbacks" / "init"
)
sys.path.insert(0, str(_agents_dir))


# -- Helpers -----------------------------------------------------------

class MockState(dict):
    """State dict that supports .get()"""
    pass


class MockCallbackContext:
    def __init__(self, state=None):
        self.state = MockState(state or {})


# -- Tests -------------------------------------------------------------

def test_turn_guard_fires_on_second_invocation():
    """Turn guard: returns None immediately when _initialized == 'true'."""
    from python_code import before_agent_callback

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "true",
    })
    result = before_agent_callback(ctx)
    assert result is None


@patch("google.cloud.firestore.Client")
def test_firestore_load_populates_state(mock_firestore_client):
    """On first call with existing Firestore doc, state is populated."""
    from python_code import before_agent_callback

    # Mock Firestore doc
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

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    result = before_agent_callback(ctx)

    assert result is None
    assert ctx.state["_initialized"] == "true"
    assert ctx.state["persona_id"] == "viktor"

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 4  # incremented
    assert profile["facts"]["name"] == "Alice"


@patch("google.cloud.firestore.Client")
def test_call_count_increments_on_repeat_caller(mock_firestore_client):
    """call_count increments for an existing caller."""
    from python_code import before_agent_callback

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "caller_id": "+15551234567",
        "call_count": 7,
        "facts": {},
        "recent_turns": [],
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    mock_firestore_client.return_value = mock_db

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    before_agent_callback(ctx)

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 8


@patch("google.cloud.firestore.Client")
def test_exception_falls_back_to_safe_default(mock_firestore_client):
    """When Firestore throws, a safe default profile is set."""
    from python_code import before_agent_callback

    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    result = before_agent_callback(ctx)

    assert result is None
    assert ctx.state["_initialized"] == "true"
    assert ctx.state["persona_id"] == "viktor"

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["caller_id"] == "+15551234567"
    assert profile["call_count"] == 1
    assert profile["facts"] == {}
