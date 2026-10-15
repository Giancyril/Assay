import logging

from fastapi import APIRouter, HTTPException, status

from backend.compare.engine import ComparativeConflictEngine
from backend.compare.models import ComparativeAuditRequest, ComparativeAuditResult
from backend.ingestion.repository import document_store

logger = logging.getLogger("compliance_agent.compare")

router = APIRouter(prefix="/api/compare", tags=["Cross-Document Conflict Engine"])

# In-memory comparison result store
_comparison_store: dict[str, ComparativeAuditResult] = {}


@router.post("/audit", response_model=ComparativeAuditResult, status_code=status.HTTP_200_OK)
async def run_comparative_audit(req: ComparativeAuditRequest):
    """Compares two uploaded documents, identifies conflicting clauses, and computes alignment score."""
    doc_a = document_store.get(req.doc_a_id)
    if not doc_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Primary document '{req.doc_a_id}' not found. Please upload it first.",
        )

    doc_b = document_store.get(req.doc_b_id)
    if not doc_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secondary document '{req.doc_b_id}' not found. Please upload it first.",
        )

    logger.info("Executing comparative audit between doc '%s' and '%s'", req.doc_a_id, req.doc_b_id)
    result = ComparativeConflictEngine.compare(
        doc_a=doc_a,
        doc_b=doc_b,
        doc_a_role=req.doc_a_role,
        doc_b_role=req.doc_b_role,
    )

    _comparison_store[result.comparison_id] = result
    return result


@router.get("/{comparison_id}", response_model=ComparativeAuditResult, status_code=status.HTTP_200_OK)
async def get_comparison_result(comparison_id: str):
    """Fetches a previously executed comparative audit result."""
    result = _comparison_store.get(comparison_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison result '{comparison_id}' not found.",
        )
    return result
