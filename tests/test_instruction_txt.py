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
