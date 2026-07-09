"""
Lightweight state store for FeedbackLoop AI.

This is the piece that makes the "one reminder per missed deadline" and
"no repeated tool calls beyond the stated exception" rules real, enforceable
constraints -- not just instructions the model is trusted to follow.

Backed by SQLite for the demo; swap for Postgres in production without
changing the interface below.
"""

import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "feedbackloop_state.db"


def init_db(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            interview_id TEXT PRIMARY KEY,
            sent_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scorecard_checks (
            interview_id TEXT PRIMARY KEY,
            check_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


@contextmanager
def _connect(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def reminder_already_sent(interview_id: str, path: str = DB_PATH) -> bool:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT 1 FROM reminders WHERE interview_id = ?", (interview_id,)
        ).fetchone()
        return row is not None


def record_reminder_sent(interview_id: str, path: str = DB_PATH) -> None:
    with _connect(path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO reminders (interview_id, sent_at) VALUES (?, ?)",
            (interview_id, time.time()),
        )
        conn.commit()


def increment_and_get_scorecard_check_count(interview_id: str, path: str = DB_PATH) -> int:
    """
    Increments the check counter for this interview and returns the new count.
    Used to enforce: at most 2 checks per interview during SLA monitoring
    (1 before the reminder, 1 after -- per the termination-conditions exception).
    """
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO scorecard_checks (interview_id, check_count)
            VALUES (?, 1)
            ON CONFLICT(interview_id) DO UPDATE SET check_count = check_count + 1
            """,
            (interview_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT check_count FROM scorecard_checks WHERE interview_id = ?",
            (interview_id,),
        ).fetchone()
        return row[0]


def reset(path: str = DB_PATH) -> None:
    """Wipes state -- useful between demo runs / eval cases."""
    with _connect(path) as conn:
        conn.execute("DELETE FROM reminders")
        conn.execute("DELETE FROM scorecard_checks")
        conn.commit()
