"""Structural guards for root_agent instruction.txt."""

from pathlib import Path

INSTRUCTION = Path("night-line/cxas_app/NightLine/agents/root_agent/instruction.txt")


def test_route_step_calls_end_session():
    """Route step must direct the LLM to call end_session, or calls hang until telephony timeout."""
    text = INSTRUCTION.read_text()
    route_start = text.index('<step name="Route">')
    route_end = text.index("</step>", route_start)
    route_block = text[route_start:route_end]
    assert "end_session" in route_block


def test_no_why_comments_in_prompt():
    """Developer rationale comments waste ~250 tokens per live call; belongs in ADRs."""
    text = INSTRUCTION.read_text()
    assert "<!-- WHY:" not in text


def test_clarify_step_has_third_attempt_backstop():
    """Without a hard third-attempt rule the LLM can loop indefinitely on noisy calls."""
    text = INSTRUCTION.read_text()
    clarify_start = text.index('<step name="Clarify">')
    clarify_end = text.index("</step>", clarify_start)
    clarify_block = text[clarify_start:clarify_end].upper()
    assert "THIRD" in clarify_block


def test_viktor_tagline_matches_personas_json():
    """Taglines in instruction.txt must match personas.json — two sources of truth diverge."""
    import json

    personas = json.loads(Path("firestore/personas.json").read_text())
    viktor_tagline = personas["viktor"]["tagline"]  # "The noir detective who's seen too much"
    text = INSTRUCTION.read_text()
    welcome_start = text.index('<step name="Welcome">')
    welcome_end = text.index("</step>", welcome_start)
    welcome_block = text[welcome_start:welcome_end]
    assert viktor_tagline.lower() in welcome_block.lower(), f"Expected '{viktor_tagline}' in welcome block"
