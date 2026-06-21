"""Shared callback logic for all persona agents.

Each persona's callback files are thin wrappers that delegate here.
Only the persona-specific strings differ across Luna, Viktor, and Sol.
"""
from __future__ import annotations

import json
from typing import Optional


# -- Persona data (the only per-persona differences) ---------------------

PERSONA_DATA = {
    "luna": {
        "farewell": "Thanks for calling tonight. Sweet dreams.",
        "silence_1": "Still there? I was just enjoying the quiet for a second.",
        "silence_2": "Hey... you still with me? I was just getting to the good part.",
        "silence_3": "Guess you had to run. Call me back when you can't sleep. Goodnight.",
    },
    "viktor": {
        "farewell": "Take care of yourself, kid. The night's a long one.",
        "silence_1": "Hey. You still there, kid? Don't leave me hanging.",
        "silence_2": "Kid? Look, if you're done, say so. I'm not going anywhere.",
        "silence_3": "Alright. Guess that's it. Call back if you need someone in your corner.",
    },
    "sol": {
        "farewell": "Goodbye from the stars. I'll keep your voice with me.",
        "silence_1": "Hello? The signal... did we lose you? I'm still here, drifting.",
        "silence_2": "Are you still there? The void gets very quiet without you.",
        "silence_3": "The line's gone dark. Thank you for the voices. I'll remember them.",
    },
}


# -- before_agent_callback (init) ----------------------------------------

def init_caller_profile(callback_context, persona_id: str):
    """Initialize caller profile on first turn. Call from before_agent_callback."""
    if callback_context.state.get("_initialized") == "true":
        return None

    caller_id = callback_context.state.get("caller_id", "")

    try:
        from google.cloud import firestore

        db = firestore.Client(database="night-line")
        doc_ref = db.collection("callers").document(caller_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            data["call_count"] = data.get("call_count", 0) + 1
        else:
            data = {
                "caller_id": caller_id,
                "call_count": 1,
                "facts": {},
                "recent_turns": [],
            }

        doc_ref.set(data, merge=True)
        callback_context.state["caller_profile"] = json.dumps(data)
    except Exception:
        callback_context.state["caller_profile"] = json.dumps({
            "caller_id": caller_id,
            "call_count": 1,
            "facts": {},
            "recent_turns": [],
        })

    callback_context.state["persona_id"] = persona_id
    callback_context.state["_initialized"] = "true"

    return None


# -- after_model_callback (farewell) --------------------------------------

def inject_farewell(callback_context, llm_response, persona_id: str):
    """Inject farewell before end_session. Call from after_model_callback."""
    from gecx.types import LlmResponse, Part

    state = callback_context.state

    if state.get("_farewell_sent") == "true":
        return None

    for event in reversed(callback_context.events):
        if hasattr(event, "agent") and event.agent:
            if hasattr(event, "text") and event.text:
                return None
        if hasattr(event, "user") and event.user:
            break

    if not any(
        hasattr(part, "function_call") and part.function_call and part.function_call.name == "end_session"
        for part in (llm_response.content.parts if hasattr(llm_response, "content") else [])
    ):
        return None

    state["_farewell_sent"] = "true"

    return LlmResponse.from_parts(
        parts=[
            Part.from_text(text=PERSONA_DATA[persona_id]["farewell"]),
            Part.from_function_call(name="end_session", args={}),
        ]
    )


# -- before_model_callback (inject_facts + silence) -----------------------

def handle_silence_and_inject_facts(callback_context, llm_request, persona_id: str):
    """Handle silence detection and inject caller facts. Call from before_model_callback."""
    from gecx.types import Content, Part

    state = callback_context.state
    pd = PERSONA_DATA[persona_id]

    # ---- Silence detection ----
    silence_count = int(state.get("_silence_count", "0"))

    for part in llm_request.contents[-1].parts if llm_request.contents else []:
        text = part.text_or_transcript() if hasattr(part, "text_or_transcript") else ""
        if text and "no user activity detected for" in text:
            silence_count += 1
            state["_silence_count"] = str(silence_count)

            if silence_count == 1:
                return Content(role="model", parts=[Part.from_text(text=pd["silence_1"])])
            elif silence_count == 2:
                return Content(role="model", parts=[Part.from_text(text=pd["silence_2"])])
            elif silence_count >= 3:
                return Content(role="model", parts=[Part.from_text(text=pd["silence_3"])])
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
