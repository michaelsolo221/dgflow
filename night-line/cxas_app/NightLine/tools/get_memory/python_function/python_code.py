"""get_memory — retrieve caller memory profile from Firestore."""

import json


def get_memory_tool(callback_context):
    """Read caller profile from Firestore. Returns empty profile on error."""
    try:
        from google.cloud import firestore

        caller_id = callback_context.state["caller_id"]
        db = firestore.Client(database="night-line")
        doc_ref = db.collection("callers").document(caller_id)
        doc = doc_ref.get()

        if doc.exists:
            return {"caller_profile": json.dumps(doc.to_dict())}

        # New caller — return empty profile
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
