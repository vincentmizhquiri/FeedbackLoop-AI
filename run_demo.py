"""
Demo CLI for FeedbackLoop AI.

Usage:
    python run_demo.py sla-check --req-id req_600
    python run_demo.py summarize --candidate-id cand_A
    python run_demo.py compare --req-id req_500
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

    args = parser.parse_args()

    if args.command == "reset-state":
        state_store.init_db()
        state_store.reset()
        print("State store reset.")
        return

    state_store.init_db()

    if args.command == "sla-check":
        prompt = f"Run SLA monitoring for req_id {args.req_id}. Check every completed interview's feedback status against its 24-hour deadline and take the appropriate action for each one per your instructions."
        result = run_agent(prompt, mode="sla_monitoring")
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
