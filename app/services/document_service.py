"""Store documents and their chunk embeddings."""

import logging
import threading
import uuid
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, load_only

from app.core.config import Settings
from app.core.exceptions import ConflictError, DocumentNotFoundError, InvalidDocumentError
from app.db.models import Document, DocumentChunk
from app.services.content_hash import sha256_hex
from app.services.document_classifier import classify_document_text
from app.services.document_processor import accepted_upload, process_document
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# shortcut: in-process thread, a restart drops a job that has not finished.
Classifier = Callable[[str, Settings], str]
JobStarter = Callable[[Callable, uuid.UUID, bytes, EmbeddingService, Settings], None]

_upload_slots = threading.Semaphore(1)
_upload_slots_settings: int | None = None
_upload_slots_lock = threading.Lock()


def _configure_upload_slots(max_concurrent: int) -> None:
    global _upload_slots, _upload_slots_settings
    with _upload_slots_lock:
        if _upload_slots_settings == max_concurrent:
            return
        _upload_slots = threading.Semaphore(max_concurrent)
        _upload_slots_settings = max_concurrent


def _start_in_thread(target, document_id, data, embeddings, settings) -> None:
    _configure_upload_slots(settings.max_concurrent_upload_jobs)

    def _run() -> None:
        _upload_slots.acquire()
        try:
            target(document_id, data, embeddings, settings)
        finally:
            _upload_slots.release()

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"document-{document_id}",
    ).start()


def run_document_job(document_id, data, embeddings, settings) -> None:
    """Extract, embed, and mark one saved document. Runs outside the upload request."""
    from app.db.database import SessionLocal, init_engine

    init_engine()
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or document.status != "processing":
            return
        DocumentService(db, embeddings, settings, start_job=lambda *_args: None).finish(document, data)
    finally:
        db.close()


class DocumentService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService,
        settings: Settings,
        start_job: JobStarter = _start_in_thread,
        classify: Classifier = classify_document_text,
    ) -> None:
        self.db = db
        self.embeddings = embeddings
        self.settings = settings
        self.start_job = start_job
        self.classify = classify

    def create_document(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> Document:
        safe_name, canonical_type = accepted_upload(
            filename,
            content_type,
            data,
            max_size=self.settings.max_upload_size_bytes,
        )
        content_hash = sha256_hex(data)
        existing = self._find_duplicate(user_id, content_hash)
        if existing is not None:
            raise ConflictError(f"This document has already been uploaded as {existing.filename}.")

        document = Document(
            id=uuid.uuid4(),
            user_id=user_id,
            filename=safe_name,
            content_type=canonical_type,
            content_hash=content_hash,
            size_bytes=len(data),
            status="processing",
        )
        try:
            self.db.add(document)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            existing = self._find_duplicate(user_id, content_hash)
            if existing is not None:
                raise ConflictError(
                    f"This document has already been uploaded as {existing.filename}."
                ) from exc
            raise
        except SQLAlchemyError:
            self.db.rollback()
            raise

        self.db.refresh(document)
        self.start_job(run_document_job, document.id, data, self.embeddings, self.settings)
        logger.info("Queued document %s", document.id)
        return document

    def finish(self, document: Document, data: bytes) -> None:
        """Turn a processing document into ready chunks, or record the failure."""
        try:
            processed = process_document(
                document.filename,
                document.content_type,
                data,
                max_size=self.settings.max_upload_size_bytes,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
                max_pdf_pages=self.settings.max_pdf_pages,
                max_extracted_text_chars=self.settings.max_extracted_text_chars,
                max_chunks=self.settings.max_chunks_per_document,
            )
            vectors = self.embeddings.embed_texts(processed.chunks)
            if len(vectors) != len(processed.chunks):
                raise RuntimeError("Embedding service returned an unexpected number of vectors.")
            full_text = "\n\n".join(processed.chunks)
            document.category = self.classify(full_text, self.settings)
            for index, (content, vector) in enumerate(zip(processed.chunks, vectors, strict=True)):
                document.chunks.append(
                    DocumentChunk(
                        id=uuid.uuid4(),
                        chunk_index=index,
                        content=content,
                        embedding=vector,
                    )
                )
            document.status = "ready"
            document.error_message = None
            self.db.commit()
            logger.info("Stored document %s with %s chunks", document.id, len(processed.chunks))
        except InvalidDocumentError as exc:
            self._mark_failed(document, exc.message)
        except Exception:
            logger.exception("Document %s failed", document.id)
            self._mark_failed(document, "Document processing failed.")

    def _find_duplicate(self, user_id: uuid.UUID, content_hash: str) -> Document | None:
        statement = (
            select(Document)
            .where(
                Document.user_id == user_id,
                Document.content_hash == content_hash,
                Document.status.in_(("processing", "ready")),
            )
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def _mark_failed(self, document: Document, message: str) -> None:
        self.db.rollback()
        current = self.db.get(Document, document.id)
        if current is None:
            return
        current.status = "failed"
        current.error_message = message
        self.db.commit()

    def list_documents(self, user_id: uuid.UUID) -> list[tuple[Document, int]]:
        statement = (
            select(Document, func.count(DocumentChunk.id))
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
        return [(document, int(count)) for document, count in self.db.execute(statement).all()]

    def get_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = self.db.get(Document, document_id)
        if document is None or document.user_id != user_id:
            raise DocumentNotFoundError(document_id)
        return document

    def list_chunks(self, user_id: uuid.UUID, document_id: uuid.UUID) -> list[DocumentChunk]:
        self.get_document(user_id, document_id)
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .options(
                load_only(
                    DocumentChunk.id,
                    DocumentChunk.document_id,
                    DocumentChunk.chunk_index,
                    DocumentChunk.content,
                )
            )
            .order_by(DocumentChunk.chunk_index)
        )
        return list(self.db.scalars(statement).all())

    def delete_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        document = self.get_document(user_id, document_id)
        try:
            self.db.delete(document)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise
        logger.info("Deleted document %s", document_id)
