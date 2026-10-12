"""Upload validation and text extraction."""

import pymupdf
import pytest

from app.core.exceptions import InvalidDocumentError
from app.services.document_processor import process_document

LIMITS = {"max_size": 1_000_000, "chunk_size": 200, "chunk_overlap": 20}


def _process(filename: str, content_type: str | None, data: bytes):
    return process_document(filename, content_type, data, **LIMITS)


def _pdf(text: str, **save_options) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    data = document.tobytes(**save_options)
    document.close()
    return data


def test_txt_upload_is_cleaned_and_chunked():
    processed = _process("notes.txt", "text/plain", b"Hello   world\n\nfrom a file")
    assert processed.filename == "notes.txt"
    assert processed.content_type == "text/plain"
    assert processed.chunks == ["Hello world from a file"]


def test_filename_path_is_stripped():
    processed = _process("../../Notes.TXT", "text/plain; charset=utf-8", b"hello")
    assert processed.filename == "Notes.TXT"
    assert processed.content_type == "text/plain"


def test_pdf_text_is_extracted():
    processed = _process("guide.pdf", "application/pdf", _pdf("Vector search"))
    assert processed.content_type == "application/pdf"
    assert processed.chunks == ["Vector search"]


def test_octet_stream_is_accepted_when_the_extension_matches():
    processed = _process("notes.txt", "application/octet-stream", b"plain text")
    assert processed.chunks == ["plain text"]


def test_rejects_unsupported_extension():
    with pytest.raises(InvalidDocumentError, match="Only PDF and TXT"):
        _process("notes.md", "text/markdown", b"hello")


def test_rejects_empty_file():
    with pytest.raises(InvalidDocumentError, match="empty"):
        _process("notes.txt", "text/plain", b"")


def test_rejects_whitespace_only_text():
    with pytest.raises(InvalidDocumentError, match="no readable text"):
        _process("notes.txt", "text/plain", b" \n\t ")


def test_rejects_file_over_the_size_limit():
    with pytest.raises(InvalidDocumentError, match="maximum size"):
        process_document(
            "notes.txt",
            "text/plain",
            b"12345",
            max_size=4,
            chunk_size=100,
            chunk_overlap=10,
        )


def test_rejects_mismatched_content_type():
    with pytest.raises(InvalidDocumentError, match="content type"):
        _process("notes.txt", "text/html", b"hello")


def test_rejects_pdf_without_header():
    with pytest.raises(InvalidDocumentError, match="not a readable PDF"):
        _process("notes.pdf", "application/pdf", b"this is not a pdf")


def test_rejects_corrupt_pdf():
    with pytest.raises(InvalidDocumentError, match="could not be read"):
        _process("notes.pdf", "application/pdf", b"%PDF-1.7 not really a pdf")


def test_rejects_blank_pdf():
    with pytest.raises(InvalidDocumentError, match="no readable text"):
        _process("blank.pdf", "application/pdf", _pdf(""))


def test_rejects_encrypted_pdf():
    data = _pdf(
        "secret",
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
    )
    with pytest.raises(InvalidDocumentError, match="Encrypted"):
        _process("secret.pdf", "application/pdf", data)


def test_rejects_missing_filename():
    with pytest.raises(InvalidDocumentError, match="filename"):
        _process("", "text/plain", b"hello")
