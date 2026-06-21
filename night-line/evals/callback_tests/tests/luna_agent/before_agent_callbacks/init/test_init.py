"""Callback tests for before_agent_callback (init)."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the callback from the eval agents copy with a unique module name
_agents_dir = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "agents" / "luna_agent" / "before_agent_callbacks" / "init"
)
_spec = importlib.util.spec_from_file_location(
    "before_agent_init_python_code",
    str(_agents_dir / "python_code.py"),
)
_before_agent_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_before_agent_module)
before_agent_callback = _before_agent_module.before_agent_callback


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
    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "true",
    })
    result = before_agent_callback(ctx)
    assert result is None


@patch("google.cloud.firestore.Client")
def test_firestore_load_populates_state(mock_firestore_client):
    """On first call with existing Firestore doc, state is populated."""
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
    assert ctx.state["persona_id"] == "luna"

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 4  # incremented
    assert profile["facts"]["name"] == "Alice"


@patch("google.cloud.firestore.Client")
def test_call_count_increments_on_repeat_caller(mock_firestore_client):
    """call_count increments for an existing caller."""
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
    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    result = before_agent_callback(ctx)

    assert result is None
    assert ctx.state["_initialized"] == "true"
    assert ctx.state["persona_id"] == "luna"

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["caller_id"] == "+15551234567"
    assert profile["call_count"] == 1
    assert profile["facts"] == {}


# -- New Caller Greeting tests -----------------------------------------

@patch("google.cloud.firestore.Client")
def test_new_caller_creates_fresh_profile(mock_firestore_client):
    """New caller (no Firestore doc): call_count=1, empty facts, is_returning=false."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False  # No existing doc — new caller
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
    mock_firestore_client.return_value = mock_db

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    before_agent_callback(ctx)

    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 1
    assert profile["facts"] == {}
    assert ctx.state["is_returning"] == "false"

# -- Returning Caller Greeting tests -----------------------------------

@patch("google.cloud.firestore.Client")
def test_returning_caller_facts_loaded(mock_firestore_client):
    """Returning caller: call_count incremented, facts loaded, is_returning=true."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "caller_id": "+15551234567",
        "call_count": 2,
        "facts": {"name": "Bob", "hobby": "painting"},
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
    assert profile["call_count"] == 3  # incremented from 2
    assert profile["facts"]["name"] == "Bob"
    assert profile["facts"]["hobby"] == "painting"
    assert ctx.state["is_returning"] == "true"


# -- Firestore-unavailable path ----------------------------------------

@patch("google.cloud.firestore.Client")
def test_firestore_unavailable_is_returning_false(mock_firestore_client):
    """When Firestore fails, is_returning defaults to false."""
    mock_firestore_client.side_effect = RuntimeError("Firestore down")

    ctx = MockCallbackContext({
        "caller_id": "+15551234567",
        "_initialized": "false",
    })
    before_agent_callback(ctx)

    assert ctx.state["is_returning"] == "false"
    profile = json.loads(ctx.state["caller_profile"])
    assert profile["call_count"] == 1
    assert profile["facts"] == {}
