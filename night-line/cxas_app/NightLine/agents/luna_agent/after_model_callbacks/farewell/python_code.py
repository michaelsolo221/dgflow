"""after_model_callback — injects farewell before end_session."""
from __future__ import annotations

from typing import Optional

from _shared.persona_callbacks import inject_farewell


def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:  # noqa: F821
    return inject_farewell(callback_context, llm_response, "luna")
