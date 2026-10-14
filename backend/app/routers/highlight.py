"""
API router for Feature 2: Visual Document Highlighting & Jump-to-Source.

Provides the DocumentHighlightMap that the frontend PDF viewer uses to overlay
colored annotation markers, render finding callouts, and enable one-click
jump-to-source navigation for each compliance finding.
"""

from fastapi import APIRouter, HTTPException, Query, status

from backend.agent.findings import findings_repository
from backend.highlight.locator import build_highlight_map
from backend.highlight.models import DocumentHighlightMap, HighlightAnnotation

router = APIRouter(prefix="/api/highlight", tags=["Visual Highlighting"])


@router.get("/{doc_id}", response_model=DocumentHighlightMap)
async def get_document_highlight_map(
    doc_id: str,
    verdict_filter: list[str] | None = Query(
        default=None, description="Filter by verdict: violation, needs_review, compliant, not_applicable"
    ),
):
    """
    Returns a complete highlight map for a document.

    The map contains per-finding HighlightAnnotations with character offsets,
    page numbers, semantic colors, tooltip text, and PDF jump-link URLs.
    Optionally filter annotations by verdict.
    """
    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings for document '{doc_id}'. Run a compliance check first.",
        )

    # Apply optional verdict filter
    if verdict_filter:
        findings = [f for f in findings if str(f.verdict) in verdict_filter]

    return build_highlight_map(doc_id, findings)


@router.get("/{doc_id}/page/{page_number}", response_model=list[HighlightAnnotation])
async def get_highlights_for_page(doc_id: str, page_number: int):
    """
    Returns all highlight annotations on a specific page.

    Optimized for PDF viewer integration where pages are rendered individually.
    """
    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings for document '{doc_id}'. Run a compliance check first.",
        )

    page_findings = [f for f in findings if f.evidence and f.evidence.page_number == page_number]

    highlight_map = build_highlight_map(doc_id, page_findings)
    return highlight_map.annotations
