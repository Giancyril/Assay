import logging

from fastapi import APIRouter, HTTPException, status

from backend.agent.findings import findings_repository
from backend.ingestion.repository import doc_repository
from backend.risk.calculator import FinancialExposureCalculator
from backend.risk.models import FinancialExposureReport

logger = logging.getLogger("compliance_agent.risk")

router = APIRouter(prefix="/api/risk", tags=["Financial Exposure & Risk Scoring"])

# Cache for evaluated risk reports: doc_id -> FinancialExposureReport
_risk_report_store: dict[str, FinancialExposureReport] = {}


@router.post(
    "/evaluate/{doc_id}",
    response_model=FinancialExposureReport,
    status_code=status.HTTP_200_OK,
)
async def evaluate_document_risk(doc_id: str):
    """Evaluates monetary liability exposure and quantitative risk scores for a document."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    logger.info("Computing financial risk exposure for doc '%s' (%d findings)", doc_id, len(findings))

    report = FinancialExposureCalculator.evaluate(document=doc, findings=findings)
    _risk_report_store[doc_id] = report
    return report


@router.get(
    "/{doc_id}",
    response_model=FinancialExposureReport,
    status_code=status.HTTP_200_OK,
)
async def get_document_risk_report(doc_id: str):
    """Fetches the financial risk report for a document, evaluating it if not yet cached."""
    if doc_id in _risk_report_store:
        return _risk_report_store[doc_id]

    # Evaluate on-demand
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    report = FinancialExposureCalculator.evaluate(document=doc, findings=findings)
    _risk_report_store[doc_id] = report
    return report
