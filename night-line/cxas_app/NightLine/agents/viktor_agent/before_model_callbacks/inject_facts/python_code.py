"""before_model_callback — inject caller facts and handle silence."""

from __future__ import annotations

import json
from typing import Optional


def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:  # noqa: F821
    from gecx.types import Content, Part

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
                    role="model", parts=[Part.from_text(text="Hey. You still there, kid? Don't leave me hanging.")]
                )
            elif silence_count == 2:
                return Content(
                    role="model",
                    parts=[Part.from_text(text="Kid? Look, if you're done, say so. I'm not going anywhere.")],
                )
            elif silence_count >= 3:
                return Content(
                    role="model",
                    parts=[
                        Part.from_text(text="Alright. Guess that's it. Call back if you need someone in your corner.")
                    ],
                )
            break

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

    llm_request.contents.append(Content(role="user", parts=[Part.from_text(text=facts_text)]))
    return None
