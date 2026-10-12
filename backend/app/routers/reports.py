
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from backend.agent.findings import findings_repository
from backend.ingestion.repository import doc_repository
from backend.reporting.generator import generate_markdown_report, generate_pdf_report
from backend.rules.models import Verdict

router = APIRouter(prefix="/api/reports", tags=["Compliance Reports"])


class ReportSummaryResponse(BaseModel):
    document_id: str
    filename: str
    total_findings: int
    compliance_score: float
    overall_status: str
    counts: dict[str, int]
    markdown_url: str
    pdf_url: str


@router.get("/{doc_id}/summary", response_model=ReportSummaryResponse)
async def get_report_summary(doc_id: str):
    """Returns metadata summary of the compliance report with download links."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings recorded for document '{doc_id}'. Please run a compliance check first."
        )

    total = len(findings)
    violations = sum(1 for f in findings if f.verdict == Verdict.VIOLATION or f.verdict == "violation")
    needs_review = sum(1 for f in findings if f.verdict == Verdict.NEEDS_REVIEW or f.verdict == "needs_review")
    compliant = sum(1 for f in findings if f.verdict == Verdict.COMPLIANT or f.verdict == "compliant")
    not_app = sum(1 for f in findings if f.verdict == Verdict.NOT_APPLICABLE or f.verdict == "not_applicable")

    score = round((compliant / total * 100), 1) if total > 0 else 0.0

    if violations > 0:
        overall_status = "NON_COMPLIANT"
    elif needs_review > 0:
        overall_status = "REQUIRES_REVIEW"
    else:
        overall_status = "COMPLIANT"

    return ReportSummaryResponse(
        document_id=doc.id,
        filename=doc.filename,
        total_findings=total,
        compliance_score=score,
        overall_status=overall_status,
        counts={
            "violation": violations,
            "needs_review": needs_review,
            "compliant": compliant,
            "not_applicable": not_app
        },
        markdown_url=f"/api/reports/{doc.id}/markdown",
        pdf_url=f"/api/reports/{doc.id}/pdf"
    )


@router.get("/{doc_id}/markdown")
async def get_markdown_report(doc_id: str):
    """Downloads or displays the Markdown compliance audit report."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings recorded for document '{doc_id}'. Please run a compliance check first."
        )

    md_content = generate_markdown_report(doc, findings)
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"inline; filename=audit_{doc.id}.md"}
    )


@router.get("/{doc_id}/pdf")
async def get_pdf_report(doc_id: str):
    """Generates and downloads the executive PDF compliance report."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found."
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    if not findings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No findings recorded for document '{doc_id}'. Please run a compliance check first."
        )

    pdf_bytes = generate_pdf_report(doc, findings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=audit_{doc.id}.pdf"}
    )
