"""Callback tests for before_model_callback (inject_facts)."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock


# Inject mock gecx.types module BEFORE importing the callback
class _MockPart:
    """Mock a CXAS Part with text_or_transcript()."""

    def __init__(self, text=""):
        self._text = text

    def text_or_transcript(self):
        return self._text

    @staticmethod
    def from_text(*, text):
        return _MockPart(text)


class _MockContent:
    """Mock a CXAS Content with a parts list."""

    def __init__(self, role="user", parts=None):
        self.role = role
        self.parts = parts or []


_mock_gecx_types = MagicMock()
_mock_gecx_types.Content = _MockContent
_mock_gecx_types.Part = _MockPart
sys.modules["gecx"] = MagicMock()
sys.modules["gecx.types"] = _mock_gecx_types

# Import the callback from the eval agents copy with a unique module name
_agents_dir = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "agents"
    / "luna_agent"
    / "before_model_callbacks"
    / "inject_facts"
)
_spec = importlib.util.spec_from_file_location(
    "before_model_inject_python_code",
    str(_agents_dir / "python_code.py"),
)
_before_model_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_before_model_module)
before_model_callback = _before_model_module.before_model_callback


# -- Helpers -----------------------------------------------------------


class MockState(dict):
    """State dict that supports .get()"""

    pass


class MockCallbackContext:
    def __init__(self, state=None):
        self.state = MockState(state or {})


class MockLlmRequest:
    """Mock LlmRequest with a contents list."""

    def __init__(self, contents=None):
        self.contents = contents if contents is not None else []


# -- Tests -------------------------------------------------------------


def test_no_facts_no_op():
    """When caller_profile has empty facts, returns None and does not modify request."""
    ctx = MockCallbackContext(
        {
            "caller_profile": json.dumps(
                {
                    "caller_id": "+15551234567",
                    "call_count": 1,
                    "facts": {},
                    "recent_turns": [],
                }
            ),
        }
    )
    llm_req = MockLlmRequest()

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 0  # No content injected


def test_facts_injected_happy_path():
    """When facts are present, they are injected into llm_request.contents."""
    ctx = MockCallbackContext(
        {
            "caller_profile": json.dumps(
                {
                    "caller_id": "+15551234567",
                    "call_count": 3,
                    "facts": {"name": "Charlie", "job": "barista"},
                    "recent_turns": [],
                }
            ),
        }
    )
    llm_req = MockLlmRequest(contents=[])

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 1
    injected_content = llm_req.contents[0]
    assert injected_content.role == "user"
    injected_text = injected_content.parts[0]._text
    assert "name: Charlie" in injected_text
    assert "job: barista" in injected_text
    assert "Use these facts naturally" in injected_text


def test_facts_injected_appends_to_existing_contents():
    """When llm_request already has contents, fact injection appends."""
    ctx = MockCallbackContext(
        {
            "caller_profile": json.dumps(
                {
                    "caller_id": "+15551234567",
                    "call_count": 2,
                    "facts": {"hobby": "cooking"},
                    "recent_turns": [],
                }
            ),
        }
    )
    existing_content = _MockContent(role="user", parts=[_MockPart("Hello")])
    llm_req = MockLlmRequest(contents=[existing_content])

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 1  # appended to existing content's parts, not new content
    assert llm_req.contents[0] is existing_content  # Original preserved
    assert len(existing_content.parts) == 2  # original "Hello" + injected facts part


def test_malformed_json_graceful_return():
    """When caller_profile is not valid JSON, returns None gracefully."""
    ctx = MockCallbackContext(
        {
            "caller_profile": "not-valid-json{{{",
        }
    )
    llm_req = MockLlmRequest(contents=[])

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 0  # Nothing injected


def test_missing_caller_profile_key_no_op():
    """When caller_profile is not in state at all, returns None."""
    ctx = MockCallbackContext({})  # No caller_profile
    llm_req = MockLlmRequest(contents=[])

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 0


def test_empty_facts_dict_no_op():
    """When facts dict exists but is empty, returns None."""
    ctx = MockCallbackContext(
        {
            "caller_profile": json.dumps(
                {
                    "caller_id": "+15551234567",
                    "call_count": 5,
                    "facts": {},
                    "recent_turns": [],
                }
            ),
        }
    )
    llm_req = MockLlmRequest(contents=[])

    result = before_model_callback(ctx, llm_req)

    assert result is None
    assert len(llm_req.contents) == 0
