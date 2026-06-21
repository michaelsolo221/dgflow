"""before_model_callback — inject caller facts and handle silence."""
from __future__ import annotations

from typing import Optional

from _shared.persona_callbacks import handle_silence_and_inject_facts


def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:  # noqa: F821
    return handle_silence_and_inject_facts(callback_context, llm_request, "luna")
