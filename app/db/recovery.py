"""Recover document rows left in processing after a crash or restart."""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Processing was interrupted. Upload the file again."


def recover_stuck_processing(engine: Engine) -> int:
    """Mark every processing document as failed so hashes can be re-uploaded."""
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE documents
                SET status = 'failed', error_message = :message
                WHERE status = 'processing'
                """
            ),
            {"message": INTERRUPTED_MESSAGE},
        )
        count = int(result.rowcount or 0)
    if count:
        logger.warning("Marked %s interrupted document(s) as failed", count)
    return count