"""
FeedbackLoop AI -- agent orchestration (OpenRouter edition).
"""

import json
import os
import time

from openai import OpenAI, RateLimitError

from . import tools
from .prompts import SYSTEM_PROMPT

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
MODEL = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "get_interview_schedule", "description": "Retrieves scheduled interviews for a req or candidate and their computed 24-hour feedback-due timestamp.", "parameters": {"type": "object", "properties": {"req_id": {"type": "string"}, "candidate_id": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "get_scorecard_status", "description": "Checks whether an interview's scorecard has been submitted and retrieves its content if so.", "parameters": {"type": "object", "properties": {"interview_id": {"type": "string"}}, "required": ["interview_id"]}}},
    {
        "type": "function",
        "function": {
            "name": "get_candidate_scorecards",
            "description": "Retrieves ALL interviews and scorecards for a single candidate in one call. Use this for single-candidate summaries -- a candidate typically has multiple panel interviews, so get_scorecard_status alone (one interview at a time) won't surface the full picture.",
            "parameters": {
                "type": "object",
                "properties": {"candidate_id": {"type": "string"}},
                "required": ["candidate_id"],
            },
        },
    },
    {"type": "function", "function": {"name": "send_reminder", "description": "Sends one templated reminder to an interviewer whose scorecard is past the SLA deadline. Never use for candidates.", "parameters": {"type": "object", "properties": {"interview_id": {"type": "string"}, "interviewer_contact": {"type": "string"}}, "required": ["interview_id", "interviewer_contact"]}}},
    {"type": "function", "function": {"name": "get_req_candidates", "description": "Retrieves all candidates currently in a requisition along with their aggregated scorecards, for cross-candidate comparison.", "parameters": {"type": "object", "properties": {"req_id": {"type": "string"}}, "required": ["req_id"]}}},
    {"type": "function", "function": {"name": "get_req_criteria", "description": "Retrieves the success criteria the recruiter and hiring manager defined together in the req's intake meeting. Must be called before any cross-candidate ranking.", "parameters": {"type": "object", "properties": {"req_id": {"type": "string"}}, "required": ["req_id"]}}},
]

MODE_LIMITS = {
    "sla_monitoring": {"get_interview_schedule": 1, "get_scorecard_status": 2, "send_reminder": 1},
    "single_candidate_summary": {"get_candidate_scorecards": 1},
    "candidate_comparison": {"get_req_criteria": 1, "get_req_candidates": 1},
}


class CallLimiter:
    def __init__(self, mode: str):
        self.mode = mode
        self.limits = MODE_LIMITS.get(mode, {})
        self.counts: dict[str, int] = {}

    def check_and_record(self, tool_name: str):
        limit = self.limits.get(tool_name)
        used = self.counts.get(tool_name, 0)
        if limit is not None and used >= limit:
            return f"Call refused: '{tool_name}' already called max {limit} time(s) for '{self.mode}'. Produce output as-is, flagging any gap."
        self.counts[tool_name] = used + 1
        return None


def _dispatch_tool(name: str, tool_input: dict):
    fn = getattr(tools, name)
    return fn(**tool_input)


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to .env")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def _create_with_retry(client, max_retries: int = 3, **kwargs):
    delay = 15
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            print(f"  (rate-limited upstream, retrying in {delay}s -- attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
            delay *= 2


def run_agent(user_message: str, mode: str, max_turns: int = 6) -> str:
    client = _get_client()
    limiter = CallLimiter(mode)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_turns):
        response = _create_with_retry(
            client,
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            extra_headers={"HTTP-Referer": "https://github.com/vincentmizhquiri/FeedbackLoop-AI", "X-Title": "FeedbackLoop AI"},
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or ""

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls],
        })

        for tc in message.tool_calls:
            name = tc.function.name
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = {}

            refusal = limiter.check_and_record(name)
            if refusal:
                result_content = json.dumps({"error": refusal})
            else:
                try:
                    result_content = json.dumps(_dispatch_tool(name, tool_input))
                except Exception as e:
                    result_content = json.dumps({"error": f"Tool execution failed: {e}"})

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_content})

    return "Reached max turns without a final answer -- treat as 'Needs manual review'."
