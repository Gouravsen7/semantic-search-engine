"""Startup recovery for interrupted uploads."""

from sqlalchemy import create_engine, text

from app.db.recovery import INTERRUPTED_MESSAGE, recover_stuck_processing


def test_recover_stuck_processing_marks_processing_as_failed():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE documents (
                    id TEXT PRIMARY KEY,
                    status VARCHAR(20) NOT NULL,
                    error_message TEXT
                )
                """
            )
        )
        conn.execute(
            text("INSERT INTO documents (id, status, error_message) VALUES ('a', 'processing', NULL)")
        )
        conn.execute(
            text("INSERT INTO documents (id, status, error_message) VALUES ('b', 'ready', NULL)")
        )
    count = recover_stuck_processing(engine)
    assert count == 1
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, error_message FROM documents WHERE id = 'a'")).one()
        assert row[0] == "failed"
        assert row[1] == INTERRUPTED_MESSAGE