from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.ingestion.models import DocumentPage, ParsedDocument
from backend.ingestion.repository import doc_repository
from backend.ingestion.service import ingest_document_bytes

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=ParsedDocument)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or DOCX contract for ingestion, structure extraction, and character offset tracking."""
    file_bytes = await file.read()
    parsed_doc = ingest_document_bytes(file_bytes=file_bytes, filename=file.filename or "unknown.pdf")
    return parsed_doc


@router.get("", response_model=list[ParsedDocument])
async def list_documents():
    """List all ingested documents with metadata and parse status."""
    return doc_repository.list_documents()


@router.get("/{doc_id}", response_model=ParsedDocument)
async def get_document(doc_id: str):
    """Retrieve full document metadata and parsed page list."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")
    return doc


@router.get("/{doc_id}/pages/{page_num}", response_model=DocumentPage)
async def get_document_page(doc_id: str, page_num: int):
    """Retrieve a specific page with character offsets and text spans."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

    if page_num < 1 or page_num > len(doc.pages):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid page number {page_num}. Document has {len(doc.pages)} pages.",
        )
    return doc.pages[page_num - 1]


@router.get("/{doc_id}/text")
async def get_document_full_text(doc_id: str):
    """Retrieve continuous full extracted document text."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "page_count": doc.page_count,
        "total_characters": len(doc.full_text),
        "text": doc.full_text,
    }


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(doc_id: str):
    """Delete a document and its stored files."""
    deleted = doc_repository.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")
    return {"message": f"Document '{doc_id}' deleted successfully."}
