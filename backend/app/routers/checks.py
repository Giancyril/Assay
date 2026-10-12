from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from backend.agent.findings import Finding, findings_repository
from backend.agent.orchestrator import check_document_against_ruleset

router = APIRouter(prefix="/api/checks", tags=["Compliance Checks"])


class RunCheckRequest(BaseModel):
    document_id: str
    ruleset_id: Optional[str] = "ruleset-nda-commercial"
    ruleset_version: Optional[str] = None
    max_concurrency: Optional[int] = 4


class CheckSummaryResponse(BaseModel):
    document_id: str
    ruleset_id: str
    ruleset_version: str
    total_findings: int
    counts: Dict[str, int]
    findings: List[Finding]


@router.post("/run", response_model=CheckSummaryResponse)
async def run_compliance_check(body: RunCheckRequest):
    """Executes parallel LangGraph compliance check agent across all rules for a document."""
    findings = await check_document_against_ruleset(
        document_id=body.document_id,
        ruleset_id=body.ruleset_id or "ruleset-nda-commercial",
        ruleset_version=body.ruleset_version,
        max_concurrency=body.max_concurrency or 4
    )

    counts = {
        "compliant": sum(1 for f in findings if f.verdict == "compliant"),
        "violation": sum(1 for f in findings if f.verdict == "violation"),
        "needs_review": sum(1 for f in findings if f.verdict == "needs_review"),
        "not_applicable": sum(1 for f in findings if f.verdict == "not_applicable"),
    }

    return CheckSummaryResponse(
        document_id=body.document_id,
        ruleset_id=body.ruleset_id or "ruleset-nda-commercial",
        ruleset_version=body.ruleset_version or "1.0.0",
        total_findings=len(findings),
        counts=counts,
        findings=findings
    )


@router.get("/{doc_id}/findings", response_model=List[Finding])
async def get_document_findings(doc_id: str):
    """Retrieve all findings for an audited document."""
    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings found for document '{doc_id}'. Run a compliance check first."
        )
    return findings


@router.get("/findings/{finding_id}", response_model=Finding)
async def get_single_finding(finding_id: str):
    """Retrieve an individual finding by ID."""
    finding = findings_repository.get_finding_by_id(finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found."
        )
    return finding
