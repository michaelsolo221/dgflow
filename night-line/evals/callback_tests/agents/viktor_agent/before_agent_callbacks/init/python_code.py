"""before_agent_callback — initialize caller profile on first turn."""
from __future__ import annotations

from typing import Optional

from _shared.persona_callbacks import init_caller_profile


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:  # noqa: F821
    return init_caller_profile(callback_context, "viktor")
