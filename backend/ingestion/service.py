from fastapi import HTTPException, status

from backend.app.config import settings
from backend.ingestion.docx_parser import parse_docx
from backend.ingestion.models import DocumentFileType, ParsedDocument
from backend.ingestion.pdf_parser import parse_pdf
from backend.ingestion.repository import doc_repository


def validate_file_upload(filename: str, file_size: int) -> DocumentFileType:
    """Validate file extension and size constraints."""
    if not filename or "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: must include a file extension (.pdf, .docx).",
        )

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Allowed types are: {', '.join(settings.ALLOWED_EXTENSIONS)}.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum permissible size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes).")

    return DocumentFileType.PDF if ext == "pdf" else DocumentFileType.DOCX


def ingest_document_bytes(file_bytes: bytes, filename: str) -> ParsedDocument:
    """
    Ingests raw file bytes, validates format, parses structure-aware spans and pages,
    and stores original and parsed manifests.
    """
    file_type = validate_file_upload(filename, len(file_bytes))

    try:
        if file_type == DocumentFileType.PDF:
            parsed_doc = parse_pdf(file_bytes, filename=filename)
        else:
            parsed_doc = parse_docx(file_bytes, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to parse document: {e!s}")

    saved_doc = doc_repository.save_document(parsed_doc, file_bytes)
    return saved_doc
