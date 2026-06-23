"""save_turn — append a conversation turn to Firestore caller memory."""



def save_turn(role, text, callback_context):
    """Save a turn (role + text) to the caller's Firestore document. Caps at 20 turns."""
    try:
        from google.cloud import firestore

        caller_id = callback_context.state["caller_id"]
        persona_id = callback_context.state.get("persona_id", "unknown")
        db = firestore.Client(database="night-line")
        doc_ref = db.collection("callers").document(caller_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
        else:
            data = {"caller_id": caller_id, "call_count": 0, "facts": {}, "recent_turns": []}

        turns = data.get("recent_turns", [])
        turns.append({"role": role, "text": text, "persona": persona_id})
        # Cap at 20 turns
        if len(turns) > 20:
            turns = turns[-20:]

        doc_ref.set({"recent_turns": turns}, merge=True)
        return {"agent_action": ""}
    except Exception:
        return {"agent_action": "Couldn't save that turn, but let's keep going."}
