from fastapi import APIRouter, HTTPException, status

from backend.agent.findings import findings_repository
from backend.redline.engine import redline_engine
from backend.redline.models import RedlineDiff

router = APIRouter(prefix="/api/redline", tags=["Automated Redlining"])


@router.get("/{doc_id}", response_model=list[RedlineDiff])
async def get_redlines_for_document(doc_id: str):
    """
    Generate word-level redlines for all actionable findings in a document.

    Returns structured diffs with inline markup ([-deleted-]{+inserted+}),
    unified diff, and a legal rationale for each remediated clause.
    """
    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings for document '{doc_id}'. Run a compliance check first.",
        )

    redlines = redline_engine.generate_all_redlines(findings)
    return redlines


@router.get("/finding/{finding_id}", response_model=RedlineDiff)
async def get_redline_for_finding(finding_id: str):
    """
    Generate a single word-level redline for a specific finding.
    """
    finding = findings_repository.get_finding_by_id(finding_id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{finding_id}' not found.")

    return redline_engine.generate_redline_for_finding(finding)
