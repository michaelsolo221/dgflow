"""before_model_callback — inject caller facts and handle silence."""

import json
from typing import Optional

from gecx.types import Content, LlmRequest, LlmResponse, Part


def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:  # noqa: F821

    state = callback_context.state

    # ---- Silence detection ----
    # Check incoming context for silence markers (voice modality)
    silence_count = int(state.get("_silence_count", "0"))

    for part in llm_request.contents[-1].parts if llm_request.contents else []:
        text = part.text_or_transcript() if hasattr(part, "text_or_transcript") else ""
        if text and "no user activity detected for" in text:
            silence_count += 1
            state["_silence_count"] = str(silence_count)

            if silence_count == 1:
                return Content(
                    role="model",
                    parts=[Part.from_text(text="Still there? I was just enjoying the quiet for a second.")],
                )
            elif silence_count == 2:
                return Content(
                    role="model",
                    parts=[Part.from_text(text="Hey... you still with me? I was just getting to the good part.")],
                )
            elif silence_count >= 3:
                return Content(
                    role="model",
                    parts=[Part.from_text(text="Guess you had to run. Call me back when you can't sleep. Goodnight.")],
                )

    # ---- Fact injection ----
    caller_profile_raw = state.get("caller_profile", "{}")
    try:
        profile = json.loads(caller_profile_raw)
    except (json.JSONDecodeError, TypeError):
        return None

    facts = profile.get("facts", {})
    if not facts:
        return None

    facts_text = "Here is what you know about the caller so far:\n"
    for key, value in facts.items():
        facts_text += f"- {key}: {value}\n"
    facts_text += "\nUse these facts naturally in conversation. Don't list them — weave them in."

    # Guard against consecutive user-role messages (rejected by some Gemini Live variants).
    fact_part = Part.from_text(text=facts_text)
    if llm_request.contents and llm_request.contents[-1].role == "user":
        llm_request.contents[-1].parts.append(fact_part)
    else:
        llm_request.contents.append(Content(role="user", parts=[fact_part]))
    return None
