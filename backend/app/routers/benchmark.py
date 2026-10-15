import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.agent.findings import findings_repository
from backend.benchmark.engine import STANDARD_CATALOG, RegulatoryCrosswalkEngine
from backend.benchmark.models import RegulatoryBenchmarkReport
from backend.ingestion.repository import doc_repository

logger = logging.getLogger("compliance_agent.benchmark")

router = APIRouter(prefix="/api/benchmark", tags=["Regulatory Benchmark & Standards Crosswalk"])

# In-memory cache: doc_id -> RegulatoryBenchmarkReport
_benchmark_cache: dict[str, RegulatoryBenchmarkReport] = {}


@router.post(
    "/evaluate/{doc_id}",
    response_model=RegulatoryBenchmarkReport,
    status_code=status.HTTP_200_OK,
)
async def evaluate_document_benchmark(doc_id: str):
    """Benchmarks a document against GDPR, HIPAA, SOC 2, and ISO 27001 compliance standards."""
    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    logger.info("Computing regulatory benchmark for '%s' with %d findings", doc_id, len(findings))

    report = RegulatoryCrosswalkEngine.evaluate(document=doc, findings=findings)
    _benchmark_cache[doc_id] = report
    return report


@router.get(
    "/standards/catalog",
    status_code=status.HTTP_200_OK,
)
async def get_standards_catalog() -> dict[str, Any]:
    """Returns the regulatory standards catalog with statutory requirements and clause mappings."""
    return {
        standard.value: [req.model_dump() for req in reqs]
        for standard, reqs in STANDARD_CATALOG.items()
    }


@router.get(
    "/{doc_id}",
    response_model=RegulatoryBenchmarkReport,
    status_code=status.HTTP_200_OK,
)
async def get_document_benchmark_report(doc_id: str):
    """Retrieves benchmark report for a document, evaluating it on-demand if not yet cached."""
    if doc_id in _benchmark_cache:
        return _benchmark_cache[doc_id]

    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    report = RegulatoryCrosswalkEngine.evaluate(document=doc, findings=findings)
    _benchmark_cache[doc_id] = report
    return report
