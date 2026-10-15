from fastapi.testclient import TestClient

from backend.app.main import app
from backend.ingestion.models import DocumentFileType, ParsedDocument
from backend.ingestion.repository import doc_repository
from backend.risk.calculator import FinancialExposureCalculator
from backend.risk.models import ExposureCategory, RiskTier

client = TestClient(app)


def _make_dummy_doc(doc_id: str, filename: str, text: str) -> ParsedDocument:
    return ParsedDocument(
        id=doc_id,
        filename=filename,
        file_type=DocumentFileType.PDF,
        file_size_bytes=len(text.encode("utf-8")),
        storage_path=f"/tmp/{filename}",
        page_count=1,
        full_text=text,
        metadata={"title": filename},
    )


def test_risk_evaluation_clean_doc():
    clean_text = (
        "The aggregate liability of either party under this agreement shall not exceed $50,000. "
        "The confidentiality term shall expire 3 years from disclosure date. "
        "Neither party agrees to any extra covenants."
    )
    doc = _make_dummy_doc("doc-clean-1", "clean_contract.pdf", clean_text)
    report = FinancialExposureCalculator.evaluate(document=doc, findings=[])

    assert report.document_id == "doc-clean-1"
    # Lacks uncapped liability risk because liability cap exists
    assert not any(i.category == ExposureCategory.UNLIMITED_LIABILITY for i in report.exposure_breakdown)
    assert report.overall_risk_score <= 25.0
    assert report.overall_risk_tier in (RiskTier.LOW, RiskTier.MEDIUM)


def test_risk_evaluation_perpetual_and_indemnity():
    risky_text = (
        "Each party agrees to maintain confidentiality in perpetual duration indefinitely. "
        "The vendor agrees to indemnify and hold harmless the customer from all third-party losses."
    )
    doc = _make_dummy_doc("doc-risky-1", "risky_nda.pdf", risky_text)
    report = FinancialExposureCalculator.evaluate(document=doc, findings=[])

    assert report.total_max_exposure_usd >= 750000.0
    categories = [i.category for i in report.exposure_breakdown]
    assert ExposureCategory.OPERATIONAL_BREACH in categories
    assert ExposureCategory.INDEMNIFICATION in categories
    assert ExposureCategory.UNLIMITED_LIABILITY in categories  # No liability cap present


def test_risk_evaluation_uncapped_liability():
    no_cap_text = "Standard mutual NDA agreement. No mention of liability limitations whatsoever."
    doc = _make_dummy_doc("doc-nocap-1", "nocap.pdf", no_cap_text)
    report = FinancialExposureCalculator.evaluate(document=doc, findings=[])

    uncapped_item = next(i for i in report.exposure_breakdown if i.category == ExposureCategory.UNLIMITED_LIABILITY)
    assert uncapped_item.risk_tier == RiskTier.CRITICAL
    assert uncapped_item.estimated_max_exposure_usd >= 1000000.0


def test_risk_api_not_found():
    res = client.post("/api/risk/evaluate/nonexistent-doc-999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_risk_api_evaluate_and_get():
    doc_id = "doc-risk-api-test"
    text = "Agreement with aggregate liability shall not exceed $10,000. Perpetual confidentiality."
    doc = _make_dummy_doc(doc_id, "test_api.pdf", text)
    doc_repository._memory_cache[doc.id] = doc

    # POST evaluate
    res = client.post(f"/api/risk/evaluate/{doc_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    assert "overall_risk_score" in data
    assert "exposure_grade" in data
    assert len(data["exposure_breakdown"]) > 0

    # GET retrieve
    get_res = client.get(f"/api/risk/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["report_id"] == data["report_id"]
