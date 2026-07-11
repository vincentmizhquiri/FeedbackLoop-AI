"""
Demo CLI for FeedbackLoop AI.

Usage:
    python run_demo.py reset-state
    python run_demo.py seed-demo
    python run_demo.py sla-check --req-id req_600
    python run_demo.py summarize --candidate-id cand_A
    python run_demo.py compare --req-id req_500

Requires OPENROUTER_API_KEY to be set in the environment (or a .env file --
see .env.example). Fixtures under data/fixtures/ stand in for the real
Greenhouse / Google Calendar / Slack APIs, so this runs with no other
credentials.
"""

import argparse
import sys

from dotenv import load_dotenv
load_dotenv()

from src import state_store
from src.agent import run_agent


def main():
    parser = argparse.ArgumentParser(description="FeedbackLoop AI demo")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sla = sub.add_parser("sla-check", help="Run the SLA monitoring pass for a req")
    p_sla.add_argument("--req-id", required=True)

    p_summary = sub.add_parser("summarize", help="Produce a single-candidate summary")
    p_summary.add_argument("--candidate-id", required=True)

    p_compare = sub.add_parser("compare", help="Produce a ranked candidate comparison for a req")
    p_compare.add_argument("--req-id", required=True)

    sub.add_parser("reset-state", help="Wipe reminder/check-count state (start fresh)")
    sub.add_parser("seed-demo", help="Seed state so int_2002 already has a reminder logged (for the escalation scenario)")

    args = parser.parse_args()

    if args.command == "reset-state":
        state_store.init_db()
        state_store.reset()
        print("State store reset.")
        return

    if args.command == "seed-demo":
        state_store.init_db()
        state_store.seed_demo_state()
        print("Demo state seeded: int_2002 now has a reminder already on record.")
        return

    state_store.init_db()

    if args.command == "sla-check":
        from datetime import datetime, timezone
        from src import tools as _tools

        interviews = _tools.get_interview_schedule(req_id=args.req_id)
        if not interviews:
            print(f"No interviews found for req_id {args.req_id}.")
            return

        print("\n" + "=" * 70)
        print(f"SLA Monitoring -- req_id {args.req_id} ({len(interviews)} interview(s))")
        print("=" * 70)

        for iv in interviews:
            now_str = datetime.now(timezone.utc).isoformat()
            prompt = (
                f"The current date and time is {now_str} (UTC). Use this as ground truth "
                f"for 'now' -- do not assume or infer today's date from anything else. "
                f"Run SLA monitoring for interview_id {iv['interview_id']} "
                f"(candidate {iv['candidate_id']}, interviewer {iv['interviewer']}, "
                f"contact {iv['interviewer_contact']}). Check this interview's feedback "
                f"status against its 24-hour deadline and take the appropriate action "
                f"per your instructions."
            )
            result = run_agent(prompt, mode="sla_monitoring")
            print(f"\n--- {iv['interview_id']} ({iv['interviewer']}) ---")
            print(result)
        print("\n" + "=" * 70)
        return

    elif args.command == "summarize":
        prompt = f"Produce a single-candidate feedback summary for candidate_id {args.candidate_id}."
        result = run_agent(prompt, mode="single_candidate_summary")

    elif args.command == "compare":
        prompt = f"Produce a ranked candidate comparison for req_id {args.req_id}."
        result = run_agent(prompt, mode="candidate_comparison")

    else:
        parser.print_help()
        sys.exit(1)

    print("\n" + "=" * 70)
    print(result)
    print("=" * 70)


if __name__ == "__main__":
    main()
