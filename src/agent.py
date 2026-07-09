"""
FeedbackLoop AI -- agent orchestration.

Wraps the Claude tool-use loop and enforces the PRD's termination conditions
as hard limits in code, not just as instructions the model is asked to
follow. If the model tries to exceed a limit, the tool dispatcher returns an
error instead of executing the call, which is what actually makes "never
call the same tool more than once" a guarantee rather than a suggestion.
"""

import json
import os

import anthropic

from . import tools
from .prompts import SYSTEM_PROMPT

MODEL = "claude-sonnet-5"

TOOL_DEFINITIONS = [
    {
        "name": "get_interview_schedule",
        "description": "Retrieves scheduled interviews for a req or candidate and their computed 24-hour feedback-due timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "req_id": {"type": "string", "description": "Requisition ID to filter by"},
                "candidate_id": {"type": "string", "description": "Candidate ID to filter by"},
            },
        },
    },
    {
        "name": "get_scorecard_status",
        "description": "Checks whether an interview's scorecard has been submitted and retrieves its content if so.",
        "input_schema": {
            "type": "object",
            "properties": {"interview_id": {"type": "string"}},
            "required": ["interview_id"],
        },
    },
    {
        "name": "send_reminder",
        "description": "Sends one templated reminder to an interviewer whose scorecard is past the SLA deadline. Never use for candidates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "interview_id": {"type": "string"},
                "interviewer_contact": {"type": "string"},
            },
            "required": ["interview_id", "interviewer_contact"],
        },
    },
    {
        "name": "get_req_candidates",
        "description": "Retrieves all candidates currently in a requisition along with their aggregated scorecards, for cross-candidate comparison.",
        "input_schema": {
            "type": "object",
            "properties": {"req_id": {"type": "string"}},
            "required": ["req_id"],
        },
    },
    {
        "name": "get_req_criteria",
        "description": "Retrieves the success criteria the recruiter and hiring manager defined together in the req's intake meeting. Must be called before any cross-candidate ranking.",
        "input_schema": {
            "type": "object",
            "properties": {"req_id": {"type": "string"}},
            "required": ["req_id"],
        },
    },
]

# Per-mode call limits, enforced in code -- mirrors the PRD's termination conditions.
MODE_LIMITS = {
    "sla_monitoring": {
        "get_interview_schedule": 1,
        "get_scorecard_status": 2,  # 1 check, then 1 re-check after a reminder
        "send_reminder": 1,
    },
    "single_candidate_summary": {
        "get_scorecard_status": 1,
    },
    "candidate_comparison": {
        "get_req_criteria": 1,
        "get_req_candidates": 1,
    },
}


class CallLimiter:
    """Tracks tool-call counts for one agent run and refuses calls past the mode's limit."""

    def __init__(self, mode: str):
        self.mode = mode
        self.limits = MODE_LIMITS.get(mode, {})
        self.counts: dict[str, int] = {}

    def check_and_record(self, tool_name: str) -> str | None:
        """Returns an error string if the call should be refused, else None and records the call."""
        limit = self.limits.get(tool_name)
        used = self.counts.get(tool_name, 0)
        if limit is not None and used >= limit:
            return (
                f"Call refused: '{tool_name}' has already been called the maximum "
                f"{limit} time(s) permitted for this request under the '{self.mode}' "
                f"termination conditions. Do not call it again -- produce your output "
                f"as-is now, flagging any remaining gap under 'Needs manual review'."
            )
        self.counts[tool_name] = used + 1
        return None


def _dispatch_tool(name: str, tool_input: dict):
    fn = getattr(tools, name)
    return fn(**tool_input)


def run_agent(user_message: str, mode: str, max_turns: int = 6) -> str:
    """
    Runs the Claude tool-use loop for one request, enforcing this mode's
    call limits. Returns the final text response.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    limiter = CallLimiter(mode)
    messages = [{"role": "user", "content": user_message}]

    for _ in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return "".join(block.text for block in response.content if block.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            refusal = limiter.check_and_record(block.name)
            if refusal:
                result_content = json.dumps({"error": refusal})
            else:
                try:
                    result = _dispatch_tool(block.name, block.input)
                    result_content = json.dumps(result)
                except Exception as e:
                    result_content = json.dumps({"error": f"Tool execution failed: {e}"})
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result_content}
            )
        messages.append({"role": "user", "content": tool_results})

    return "Reached max turns without a final answer -- treat as 'Needs manual review'."
