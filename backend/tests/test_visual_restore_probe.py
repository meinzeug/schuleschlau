"""Same signed-replay check as the deploy preflight, on SQLite and PostgreSQL."""
import sys
from pathlib import Path

from schulpilot.db import DB

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
from visual_restore_probe import probe  # noqa: E402


def test_visual_review_signed_erasure_replay_on_isolated_database():
    with DB.begin() as db:
        probe(db, "synthetic-test-key")
