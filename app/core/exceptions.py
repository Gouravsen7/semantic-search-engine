"""Application errors translated into HTTP responses."""

from uuid import UUID


class AppError(Exception):
    """Base error that the API renders as JSON."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidDocumentError(AppError):
    """The upload cannot be processed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class DocumentNotFoundError(AppError):
    """No document exists for the given id."""

    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found.", status_code=404)


class UnauthorizedError(AppError):
    """The caller is not signed in, or the credentials are wrong."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message, status_code=401)


class ConflictError(AppError):
    """The request clashes with an existing record."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)
