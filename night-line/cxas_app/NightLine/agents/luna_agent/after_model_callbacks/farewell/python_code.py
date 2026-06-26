"""after_model_callback — injects farewell before end_session."""


def after_model_callback(callback_context, llm_response):
    state = callback_context.state

    # Session-level guard — only farewell once
    if state.get("_farewell_sent") == "true":
        return None

    # Multi-model-call guard — check events in reverse
    for event in reversed(callback_context.events):
        if hasattr(event, "agent") and event.agent:
            # Found an agent event before a user event — skip injection
            if hasattr(event, "text") and event.text:
                return None
        if hasattr(event, "user") and event.user:
            # Found a user event — safe to inject
            break

    # Check if the model response contains an end_session function call
    if not any(
        hasattr(part, "function_call") and part.function_call and part.function_call.name == "end_session"
        for part in (llm_response.content.parts if hasattr(llm_response, "content") else [])
    ):
        return None

    # Inject farewell before end_session
    state["_farewell_sent"] = "true"

    return LlmResponse.from_parts(
        parts=[
            Part.from_text(text="Thanks for calling tonight. Sweet dreams."),
            Part.from_function_call(name="end_session", args={}),
        ]
    )
