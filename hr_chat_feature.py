from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CandidateHistoryEntry:
    req_code: str
    title: str
    stage_reached: str
    outcome: str
    date: str


@dataclass
class CandidateSynthesis:
    candidate_name: str
    label: str
    signal_score: float
    scorecard_count: int
    scorecard_strengths: List[str] = field(default_factory=list)
    conflict_flag: bool = False
    excluded_reasons: List[str] = field(default_factory=list)


def build_rationale(synthesis: CandidateSynthesis, history: List[CandidateHistoryEntry]) -> str:
    """Generate compact rationale text that stays grounded in filtered synthesis data."""
    strengths = ", ".join(synthesis.scorecard_strengths) if synthesis.scorecard_strengths else "insufficient signal"
    base = (
        f"{synthesis.candidate_name} is marked as {synthesis.label} with a signal score of {synthesis.signal_score:.2f} "
        f"across {synthesis.scorecard_count} scorecards. The strongest evidence was {strengths}."
    )

    if synthesis.conflict_flag:
        base += " The panel showed a conflict signal, so the recommendation should be treated cautiously."

    if synthesis.excluded_reasons:
        base += " Insufficient data is available because the system excluded problematic feedback."

    if history:
        latest = history[0]
        base += (
            f" Historical context: this candidate was previously seen on {latest.req_code} ({latest.title}) "
            f"and reached {latest.stage_reached} with outcome {latest.outcome} on {latest.date}."
        )

    return base


def build_chat_prompt(candidate_name: str, label: str, history: List[CandidateHistoryEntry]) -> str:
    """Draft an HR-facing chat prompt for the header AI assistant panel."""
    history_block = ""
    if history:
        history_block = "\n".join(
            [
                f"- {entry.req_code}: {entry.title} | stage {entry.stage_reached} | outcome {entry.outcome} | {entry.date}"
                for entry in history
            ]
        )

    return f"""HR AI Chat Session
Header: {candidate_name}
Recommendation buttons: Strong Hire | Lean Hire | Conflicted | Optional
Status colors: Green = Strong Hire, Yellow = Lean Hire, Red = Conflicted
Candidate evaluation cards should scroll horizontally and highlight the selected recommendation.
Historical hiring context:
{history_block or 'No prior requisition history found.'}
Use the applicant's prior history and current scorecard evidence to answer recruiter questions about fit for the role.
"""
