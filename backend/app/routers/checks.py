
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.agent.findings import Finding, findings_repository
from backend.agent.orchestrator import check_document_against_ruleset

router = APIRouter(prefix="/api/checks", tags=["Compliance Checks"])


class RunCheckRequest(BaseModel):
    document_id: str
    ruleset_id: str | None = "ruleset-nda-commercial"
    ruleset_version: str | None = None
    max_concurrency: int | None = 4


class CheckSummaryResponse(BaseModel):
    document_id: str
    ruleset_id: str
    ruleset_version: str
    total_findings: int
    counts: dict[str, int]
    findings: list[Finding]


class ReviewFindingRequest(BaseModel):
    reviewer_status: str  # "confirmed", "overridden", "not_applicable"
    reviewer_override_reason: str | None = None
    reviewed_by: str | None = "compliance_reviewer"


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


@router.get("/{doc_id}/findings", response_model=list[Finding])
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


@router.patch("/findings/{finding_id}/review", response_model=Finding)
async def review_finding(finding_id: str, body: ReviewFindingRequest):
    """Reviewer Gate: Allows human compliance analyst to confirm, override, or mark a finding N/A."""
    valid_statuses = {"pending", "confirmed", "overridden", "not_applicable"}
    if body.reviewer_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reviewer status '{body.reviewer_status}'. Must be one of: {', '.join(valid_statuses)}"
        )

    if body.reviewer_status == "overridden" and not body.reviewer_override_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An override reason is required when overriding a finding."
        )

    updated = findings_repository.update_finding(
        finding_id=finding_id,
        reviewer_status=body.reviewer_status,
        override_reason=body.reviewer_override_reason,
        reviewed_by=body.reviewed_by
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found."
        )

    return updated
