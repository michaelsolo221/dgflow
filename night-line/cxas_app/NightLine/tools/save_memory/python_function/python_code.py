"""save_memory — store a fact about the caller in Firestore."""

import json


def save_memory(key, value, callback_context):
    """Merge a fact (key/value) into the caller's Firestore facts map."""
    try:
        from google.cloud import firestore

        caller_id = callback_context.state["caller_id"]
        db = firestore.Client(database="night-line")
        doc_ref = db.collection("callers").document(caller_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
        else:
            data = {"caller_id": caller_id, "call_count": 0, "facts": {}, "recent_turns": []}

        facts = data.get("facts", {})
        facts[key] = value
        doc_ref.set({"facts": facts}, merge=True)
        return {"agent_action": ""}
    except Exception:
        return {"agent_action": "Couldn't save that, but I'll remember it myself."}
