"""before_agent_callback — initialize caller profile on first turn."""

import json


def before_agent_callback(callback_context):
    # Turn guard — skip init on subsequent turns
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
        callback_context.state["caller_profile"] = json.dumps(
            {
                "caller_id": caller_id,
                "call_count": 1,
                "facts": {},
                "recent_turns": [],
            }
        )

    callback_context.state["persona_id"] = "viktor"
    callback_context.state["_initialized"] = "true"

    return None
