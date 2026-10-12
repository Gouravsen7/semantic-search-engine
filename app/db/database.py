"""SQLAlchemy engine, sessions, and schema setup."""

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None


class Base(DeclarativeBase):
    pass


def init_engine(database_url: str | None = None) -> None:
    """Create the engine once. Later calls do nothing."""
    global engine, SessionLocal
    if engine is not None:
        return

    from app.core.config import get_settings

    url = database_url or get_settings().database_url
    engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db():
    """FastAPI dependency that yields a database session."""
    init_engine()
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _reject_legacy_schema(connection) -> None:
    """Stop when an older database has documents that are not owned by a user."""
    legacy = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'documents'
            )
            AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'documents'
                  AND column_name = 'user_id'
            )
            """
        )
    ).scalar()
    if legacy:
        raise RuntimeError(
            "Existing database has documents without users. Reset it with: docker compose down -v"
        )


def _ensure_document_status(connection) -> None:
    """Add processing status to a database created before background uploads."""
    connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status VARCHAR(20)"))
    connection.execute(text("UPDATE documents SET status = 'ready' WHERE status IS NULL"))
    connection.execute(text("ALTER TABLE documents ALTER COLUMN status SET NOT NULL"))
    connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT"))
    connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"))
    connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS category VARCHAR(32)"))
    connection.execute(
        text("UPDATE documents SET category = 'General' WHERE status = 'ready' AND category IS NULL")
    )
    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_user_content_hash
            ON documents (user_id, content_hash)
            WHERE content_hash IS NOT NULL AND status IN ('processing', 'ready')
            """
        )
    )


def init_db(retries: int = 5, delay_seconds: float = 1.0) -> None:
    """Create the pgvector extension, tables, and the embedding index."""
    from app.db import models  # noqa: F401

    init_engine()
    if engine is None:
        raise RuntimeError("Database engine is not initialized")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                _reject_legacy_schema(connection)
            Base.metadata.create_all(bind=engine)
            with engine.begin() as connection:
                _ensure_document_status(connection)
                connection.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
                        ON document_chunks
                        USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                        """
                    )
                )
            from app.core.config import get_settings
            from app.db.recovery import recover_stuck_processing

            if get_settings().recover_stuck_processing_on_startup:
                recover_stuck_processing(engine)
            logger.info("Database schema is ready")
            return
        except RuntimeError:
            raise
        except Exception as exc:
            last_error = exc
            logger.warning("Database not ready (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay_seconds)

    assert last_error is not None
    raise last_error
