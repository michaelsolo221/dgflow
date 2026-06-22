"""get_memory — retrieve caller memory profile, state-cached or from Firestore."""

import json


def get_memory(callback_context):
    """Return caller profile from state cache. Falls back to Firestore if missing."""
    # State cache path — populated by before_agent_callback/init
    cached = callback_context.state.get("caller_profile", "")
    if cached and cached != "{}":
        return {"caller_profile": cached}

    # Firestore fallback — only when state cache is missing
    try:
        from google.cloud import firestore

        caller_id = callback_context.state["caller_id"]
        db = firestore.Client(database="night-line")
        doc_ref = db.collection("callers").document(caller_id)
        doc = doc_ref.get()

        if doc.exists:
            return {"caller_profile": json.dumps(doc.to_dict())}

        return {
            "caller_profile": json.dumps({
                "caller_id": caller_id,
                "call_count": 0,
                "facts": {},
                "recent_turns": [],
            })
        }
    except Exception:
        return {"agent_action": "Memory is unavailable right now, but I'm still listening."}
