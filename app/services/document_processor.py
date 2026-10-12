"""Extract, clean, and validate uploaded PDF and TXT files."""

from dataclasses import dataclass

import pymupdf

from app.core.exceptions import InvalidDocumentError
from app.utils.text_chunker import chunk_text, clean_text

PDF_EXTENSION = ".pdf"
TXT_EXTENSION = ".txt"
ALLOWED_EXTENSIONS = {PDF_EXTENSION, TXT_EXTENSION}
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
TXT_CONTENT_TYPES = {"text/plain", "application/octet-stream"}


@dataclass(frozen=True)
class ProcessedUpload:
    filename: str
    content_type: str
    chunks: list[str]


def accepted_upload(
    filename: str,
    content_type: str | None,
    data: bytes,
    *,
    max_size: int,
) -> tuple[str, str]:
    """Reject a bad file before any text extraction."""
    safe_name = safe_filename(filename)
    extension = _extension(safe_name)
    _validate_upload(extension, content_type, data, max_size)
    return safe_name, _canonical_content_type(extension)


def process_document(
    filename: str,
    content_type: str | None,
    data: bytes,
    *,
    max_size: int,
    chunk_size: int,
    chunk_overlap: int,
    max_pdf_pages: int = 200,
    max_extracted_text_chars: int = 2_000_000,
    max_chunks: int = 2_000,
) -> ProcessedUpload:
    """Validate an upload and return cleaned text chunks."""
    safe_name, canonical_type = accepted_upload(
        filename,
        content_type,
        data,
        max_size=max_size,
    )
    extension = _extension(safe_name)

    text = clean_text(extract_text(extension, data, max_pdf_pages=max_pdf_pages))
    if len(text) > max_extracted_text_chars:
        raise InvalidDocumentError(
            f"Extracted text exceeds the limit of {max_extracted_text_chars} characters."
        )
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    if len(chunks) > max_chunks:
        raise InvalidDocumentError(f"Document would exceed the limit of {max_chunks} chunks.")
    if not chunks:
        raise InvalidDocumentError("The document has no readable text.")

    return ProcessedUpload(
        filename=safe_name,
        content_type=canonical_type,
        chunks=chunks,
    )


def safe_filename(filename: str) -> str:
    cleaned = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if not cleaned or cleaned in {".", ".."} or "\x00" in cleaned:
        raise InvalidDocumentError("A filename is required.")
    if len(cleaned) > 255:
        raise InvalidDocumentError("Filename is too long.")
    return cleaned


def extract_text(extension: str, data: bytes, *, max_pdf_pages: int = 200) -> str:
    if extension == TXT_EXTENSION:
        return _decode_text(data)
    if extension == PDF_EXTENSION:
        return _extract_pdf(data, max_pdf_pages=max_pdf_pages)
    raise InvalidDocumentError("Only PDF and TXT files are supported.")


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot <= 0:
        raise InvalidDocumentError("Only PDF and TXT files are supported.")
    return filename[dot:].lower()


def _normalize_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _canonical_content_type(extension: str) -> str:
    if extension == PDF_EXTENSION:
        return "application/pdf"
    return "text/plain"


def _validate_upload(extension: str, content_type: str | None, data: bytes, max_size: int) -> None:
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidDocumentError("Only PDF and TXT files are supported.")
    if len(data) == 0:
        raise InvalidDocumentError("The uploaded file is empty.")
    if len(data) > max_size:
        limit_mb = max_size / (1024 * 1024)
        raise InvalidDocumentError(
            f"File exceeds the maximum size of {max_size} bytes ({limit_mb:g} MB)."
        )

    normalized = _normalize_content_type(content_type)
    if extension == PDF_EXTENSION:
        if normalized and normalized not in PDF_CONTENT_TYPES:
            raise InvalidDocumentError("The file content type does not match a PDF.")
        if not data.startswith(b"%PDF"):
            raise InvalidDocumentError("The file is not a readable PDF.")
        return

    if normalized and normalized not in TXT_CONTENT_TYPES:
        raise InvalidDocumentError("The file content type does not match a text file.")
    if data.startswith(b"%PDF"):
        raise InvalidDocumentError("The file content does not match a text document.")


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _extract_pdf(data: bytes, *, max_pdf_pages: int) -> str:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise InvalidDocumentError("The PDF could not be read.") from exc

    try:
        if document.is_encrypted and not document.authenticate(""):
            raise InvalidDocumentError("Encrypted PDFs are not supported.")
        if document.page_count == 0:
            raise InvalidDocumentError("The PDF has no pages.")
        if document.page_count > max_pdf_pages:
            raise InvalidDocumentError(f"PDF exceeds the page limit of {max_pdf_pages}.")
        return "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()
