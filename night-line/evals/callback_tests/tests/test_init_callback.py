"""Callback tests for before_agent_callback (init) — all personas."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PERSONAS = ["luna", "viktor", "sol"]


class MockState(dict):
    pass


class MockCallbackContext:
    def __init__(self, state=None):
        self.state = MockState(state or {})


def _import_for_persona(persona: str):
    """Re-import callback from the persona's agent dir."""
    agent_dir = (
        Path(__file__).resolve().parent.parent
        / "agents" / f"{persona}_agent" / "before_agent_callbacks" / "init"
    )
    sys.path.insert(0, str(agent_dir))
    # evict cached module so re-import picks up the right persona's code
    sys.modules.pop("python_code", None)
    import importlib
    mod = importlib.import_module("python_code")
    return mod.before_agent_callback


def test_turn_guard_fires_on_second_invocation():
    for persona in PERSONAS:
        callback = _import_for_persona(persona)
        ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "true"})
        assert callback(ctx) is None


@patch("google.cloud.firestore.Client")
def test_firestore_load_populates_state(mock_firestore_client):
    for persona in PERSONAS:
        callback = _import_for_persona(persona)
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "caller_id": "+15551234567", "call_count": 3,
            "facts": {"name": "Alice"}, "recent_turns": [{"role": "user", "text": "Hi"}],
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore_client.return_value = mock_db

        ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
        result = callback(ctx)

        assert result is None
        assert ctx.state["_initialized"] == "true"
        assert ctx.state["persona_id"] == persona
        profile = json.loads(ctx.state["caller_profile"])
        assert profile["call_count"] == 4
        assert profile["facts"]["name"] == "Alice"


@patch("google.cloud.firestore.Client")
def test_call_count_increments_on_repeat_caller(mock_firestore_client):
    for persona in PERSONAS:
        callback = _import_for_persona(persona)
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "caller_id": "+15551234567", "call_count": 7,
            "facts": {}, "recent_turns": [],
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore_client.return_value = mock_db

        ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
        callback(ctx)

        profile = json.loads(ctx.state["caller_profile"])
        assert profile["call_count"] == 8


@patch("google.cloud.firestore.Client")
def test_exception_falls_back_to_safe_default(mock_firestore_client):
    for persona in PERSONAS:
        callback = _import_for_persona(persona)
        mock_firestore_client.side_effect = RuntimeError("Firestore down")

        ctx = MockCallbackContext({"caller_id": "+15551234567", "_initialized": "false"})
        result = callback(ctx)

        assert result is None
        assert ctx.state["_initialized"] == "true"
        assert ctx.state["persona_id"] == persona
        profile = json.loads(ctx.state["caller_profile"])
        assert profile["caller_id"] == "+15551234567"
        assert profile["call_count"] == 1
        assert profile["facts"] == {}
