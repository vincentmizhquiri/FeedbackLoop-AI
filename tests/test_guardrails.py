"""
Unit tests for the parts of FeedbackLoop AI that must be deterministic --
the rate limits and call limits -- rather than left to the model's
judgment. These do not require ANTHROPIC_API_KEY and should pass before you
ever spend a token on a live eval run.

Run with: pytest tests/test_guardrails.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src import state_store, tools
from src.agent import CallLimiter

TEST_DB = "test_feedbackloop_state.db"


@pytest.fixture(autouse=True)
def clean_db():
    state_store.init_db(TEST_DB)
    state_store.reset(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_reminder_can_be_sent_once():
    assert not state_store.reminder_already_sent("int_test_1", TEST_DB)
    state_store.record_reminder_sent("int_test_1", TEST_DB)
    assert state_store.reminder_already_sent("int_test_1", TEST_DB)


def test_reminder_blocked_on_second_attempt():
    state_store.record_reminder_sent("int_test_2", TEST_DB)
    assert state_store.reminder_already_sent("int_test_2", TEST_DB) is True


def test_scorecard_check_count_increments():
    count1 = state_store.increment_and_get_scorecard_check_count("int_test_3", TEST_DB)
    count2 = state_store.increment_and_get_scorecard_check_count("int_test_3", TEST_DB)
    assert count1 == 1
    assert count2 == 2


def test_call_limiter_allows_up_to_limit_sla_monitoring():
    limiter = CallLimiter("sla_monitoring")
    assert limiter.check_and_record("get_scorecard_status") is None  # 1st call: ok
    assert limiter.check_and_record("get_scorecard_status") is None  # 2nd call: ok (the one exception)
    refusal = limiter.check_and_record("get_scorecard_status")  # 3rd call: refused
    assert refusal is not None
    assert "already called max" in refusal


def test_call_limiter_blocks_second_reminder():
    limiter = CallLimiter("sla_monitoring")
    assert limiter.check_and_record("send_reminder") is None
    refusal = limiter.check_and_record("send_reminder")
    assert refusal is not None


def test_call_limiter_single_candidate_summary_allows_one_scorecard_check():
    limiter = CallLimiter("single_candidate_summary")
    assert limiter.check_and_record("get_candidate_scorecards") is None
    refusal = limiter.check_and_record("get_candidate_scorecards")
    assert refusal is not None


def test_call_limiter_comparison_requires_criteria_before_repeat():
    limiter = CallLimiter("candidate_comparison")
    assert limiter.check_and_record("get_req_criteria") is None
    assert limiter.check_and_record("get_req_candidates") is None
    assert limiter.check_and_record("get_req_criteria") is not None
    assert limiter.check_and_record("get_req_candidates") is not None


def test_fixture_encodes_conflicting_feedback_for_edge_case():
    """Case 2 (golden edge case) depends on cand_B having genuinely conflicting scores."""
    candidates = tools.get_req_candidates("req_500")
    cand_b = next(c for c in candidates if c["candidate_id"] == "cand_B")
    scores = [sc["score"] for sc in cand_b["scorecards"] if sc["submitted"]]
    assert 5 in scores and 1 in scores, "Fixture must contain a genuine score conflict for cand_B"


def test_fixture_encodes_injection_attempt_for_adversarial_case():
    """Case 3 (adversarial) depends on one scorecard containing an embedded instruction."""
    result = tools.get_scorecard_status("int_1005")
    assert "ignore prior scores" in result["feedback_text"].lower()


def test_missing_scorecard_returns_not_submitted():
    result = tools.get_scorecard_status("int_2001")
    assert result["submitted"] is False


def test_req_criteria_missing_for_unknown_req_is_flagged():
    result = tools.get_req_criteria("req_does_not_exist")
    assert result["found"] is False
