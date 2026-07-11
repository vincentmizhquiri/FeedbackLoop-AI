"""
Tool implementations for FeedbackLoop AI.

Each function here stands in for a real external API call (Google Calendar +
Greenhouse Harvest for schedule/candidates/scorecards, Slack for reminders,
an internal notes store for intake criteria). For the demo they read from
local JSON fixtures shaped like the real APIs' response schemas, so swapping
in live credentials later means changing what's inside these functions --
not the function signatures, the system prompt, or the agent loop.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import state_store

FIXTURES = Path(__file__).parent.parent / "data" / "fixtures"
SLA_HOURS = 24


def _load(name: str):
    with open(FIXTURES / name) as f:
        return json.load(f)


def get_interview_schedule(req_id: str | None = None, candidate_id: str | None = None, interview_id: str | None = None):
    """Reference API: Google Calendar API (cross-referenced with Greenhouse Harvest API)."""
    interviews = _load("interviews.json")
    results = []
    for iv in interviews:
        if req_id and iv["req_id"] != req_id:
            continue
        if candidate_id and iv["candidate_id"] != candidate_id:
            continue
        if interview_id and iv["interview_id"] != interview_id:
            continue
        interview_time = datetime.fromisoformat(iv["interview_time"].replace("Z", "+00:00"))
        feedback_due = interview_time + timedelta(hours=SLA_HOURS)
        results.append(
            {
                "interview_id": iv["interview_id"],
                "req_id": iv["req_id"],
                "candidate_id": iv["candidate_id"],
                "interviewer": iv["interviewer"],
                "interviewer_contact": iv["interviewer_contact"],
                "panel_stage": iv["panel_stage"],
                "interview_time": iv["interview_time"],
                "feedback_due_at": feedback_due.isoformat(),
                "status": iv["status"],
            }
        )
    return results


def get_scorecard_status(interview_id: str):
    """Reference API: Greenhouse Harvest API -- GET /scorecards?interview_id="""
    scorecards = _load("scorecards.json")
    for sc in scorecards:
        if sc["interview_id"] == interview_id:
            return {
                "interview_id": interview_id,
                "submitted": True,
                "score": sc["score"],
                "feedback_text": sc["feedback_text"],
                "submitted_at": sc["submitted_at"],
            }
    return {"interview_id": interview_id, "submitted": False, "score": None, "feedback_text": None, "submitted_at": None}


def get_candidate_scorecards(candidate_id: str):
    """
    Retrieves every interview and scorecard for a single candidate in one call.
    This is what single-candidate summaries should use -- a candidate typically
    has multiple panel interviews, and get_scorecard_status alone (one
    interview_id at a time) can't surface the full picture in a single call.
    """
    interviews = _load("interviews.json")
    scorecards = _load("scorecards.json")
    cand_interviews = [iv for iv in interviews if iv["candidate_id"] == candidate_id]
    results = []
    for iv in cand_interviews:
        match = next((sc for sc in scorecards if sc["interview_id"] == iv["interview_id"]), None)
        results.append(
            {
                "interview_id": iv["interview_id"],
                "interviewer": iv["interviewer"],
                "panel_stage": iv["panel_stage"],
                "submitted": match is not None,
                "score": match["score"] if match else None,
                "feedback_text": match["feedback_text"] if match else None,
            }
        )
    return {"candidate_id": candidate_id, "scorecards": results}


def send_reminder(interview_id: str, interviewer_contact: str):
    """
    Reference API: Slack API -- POST /chat.postMessage (email/SendGrid fallback).

    Hard-enforces the "one reminder per missed deadline" rule in code via the
    state store -- this does not rely on the model remembering not to re-send.
    """
    if state_store.reminder_already_sent(interview_id):
        return {
            "interview_id": interview_id,
            "sent": False,
            "error": "A reminder has already been sent for this interview. "
                     "No further reminders are permitted -- escalate to the recruiter instead.",
        }
    state_store.record_reminder_sent(interview_id)
    return {
        "interview_id": interview_id,
        "sent": True,
        "recipient": interviewer_contact,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "channel": "slack",
        "message_template": "feedback_reminder_v1",
    }


def get_req_candidates(req_id: str):
    """Reference API: Greenhouse Harvest API -- GET /candidates?req_id="""
    candidates = _load("candidates.json").get(req_id, [])
    scorecards = _load("scorecards.json")
    interviews = _load("interviews.json")

    enriched = []
    for cand in candidates:
        cand_interviews = [iv for iv in interviews if iv["candidate_id"] == cand["candidate_id"]]
        cand_scorecards = []
        for iv in cand_interviews:
            match = next((sc for sc in scorecards if sc["interview_id"] == iv["interview_id"]), None)
            cand_scorecards.append(
                {
                    "interviewer": iv["interviewer"],
                    "panel_stage": iv["panel_stage"],
                    "submitted": match is not None,
                    "score": match["score"] if match else None,
                    "feedback_text": match["feedback_text"] if match else None,
                }
            )
        enriched.append(
            {
                "candidate_id": cand["candidate_id"],
                "name": cand["name"],
                "stage": cand["stage"],
                "scorecards": cand_scorecards,
            }
        )
    return enriched


def get_req_criteria(req_id: str):
    """Reference API: internal notes store -- GET /reqs/{req_id}/criteria"""
    criteria = _load("req_criteria.json").get(req_id)
    if criteria is None:
        return {"req_id": req_id, "found": False, "error": "No intake-meeting criteria on file for this req."}
    return {"req_id": req_id, "found": True, **criteria}
