from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.indexing.models import ClauseChunk, RetrievalResult
from backend.indexing.service import clause_index_service

router = APIRouter(prefix="/api/documents", tags=["Indexing & Retrieval"])


class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    alpha: float = 0.5  # 0 = pure lexical, 1 = pure vector, 0.5 = balanced hybrid


@router.post("/{doc_id}/index", response_model=list[ClauseChunk])
async def trigger_document_indexing(doc_id: str):
    """Parse structure-aware clause chunks from document and build hybrid index."""
    return clause_index_service.index_document(doc_id)


@router.get("/{doc_id}/clauses", response_model=list[ClauseChunk])
async def get_document_clauses(doc_id: str):
    """Retrieve all structure-aware clauses extracted from document."""
    return clause_index_service.get_document_clauses(doc_id)


@router.post("/{doc_id}/search", response_model=list[RetrievalResult])
async def search_document_clauses(doc_id: str, body: SearchQueryRequest):
    """Perform hybrid retrieval on document clauses using full-text and vector search."""
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")
    return clause_index_service.search_document(
        doc_id=doc_id,
        query=body.query,
        top_k=body.top_k,
        alpha=body.alpha
    )
