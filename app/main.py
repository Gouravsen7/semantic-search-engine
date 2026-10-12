"""Semantic search API entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import auth, documents, health, search
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.database import init_db

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Health", "description": "Service and database status."},
    {"name": "Auth", "description": "Register, log in, and read the current user."},
    {"name": "Documents", "description": "Upload, list, fetch, and delete the signed-in user's documents."},
    {"name": "Search", "description": "Semantic search over stored document chunks."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = get_settings()
    if settings.init_db_on_startup:
        init_db()
    logger.info("Semantic search API is ready")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Semantic Search Engine",
        summary="Upload documents and search them with natural language.",
        description=(
            "API for extracting text from PDF and TXT files, storing chunk embeddings "
            f"in PostgreSQL with pgvector, and searching them with {settings.embedding_model}."
        ),
        version="1.0.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )
    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": _validation_message(exc)})

    @app.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content={"message": message})

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("Database error: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"message": "Database is unavailable."})


def _validation_message(exc: RequestValidationError) -> str:
    """Report the field that failed, not a generic validation error."""
    error = exc.errors()[0]
    location = [str(part) for part in error.get("loc", ())]
    if location and location[0] in {"body", "query", "path"}:
        location = location[1:]
    field = ".".join(location)
    text = str(error.get("msg", "Invalid request."))
    if text.startswith("Value error, "):
        text = text.removeprefix("Value error, ")
    return f"{field}: {text}" if field else text


app = create_app()
