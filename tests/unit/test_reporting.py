import pytest
from fastapi.testclient import TestClient

from backend.agent.orchestrator import check_document_against_ruleset
from backend.app.main import app
from backend.reporting.generator import generate_markdown_report, generate_pdf_report
from tests.unit.test_agent import create_audit_test_doc

client = TestClient(app)


@pytest.fixture(scope="module")
def audited_doc_and_findings():
    """Runs a full audit once for reporting tests."""
    doc = create_audit_test_doc()
    import asyncio

    findings = asyncio.run(check_document_against_ruleset(doc.id, "ruleset-nda-commercial"))
    return doc, findings


def test_markdown_report_generation(audited_doc_and_findings):
    doc, findings = audited_doc_and_findings
    md = generate_markdown_report(doc, findings)

    assert "# Contract Compliance Audit Report" in md
    assert doc.filename in md
    assert "## Executive Summary" in md
    assert "## Detailed Findings" in md
    assert "NDA-02" in md
    assert "NDA-05" in md
    assert "Legal Disclaimer:" in md
    assert "Compliance Score:" in md


def test_pdf_report_generation(audited_doc_and_findings):
    doc, findings = audited_doc_and_findings
    pdf_bytes = generate_pdf_report(doc, findings)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_reports_api_summary_endpoint(audited_doc_and_findings):
    doc, _ = audited_doc_and_findings
    response = client.get(f"/api/reports/{doc.id}/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == doc.id
    assert data["total_findings"] == 10
    assert data["overall_status"] in ["NON_COMPLIANT", "REQUIRES_REVIEW", "COMPLIANT"]
    assert "counts" in data
    assert data["counts"]["violation"] >= 2
    assert data["markdown_url"] == f"/api/reports/{doc.id}/markdown"
    assert data["pdf_url"] == f"/api/reports/{doc.id}/pdf"


def test_reports_api_markdown_endpoint(audited_doc_and_findings):
    doc, _ = audited_doc_and_findings
    response = client.get(f"/api/reports/{doc.id}/markdown")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "# Contract Compliance Audit Report" in response.text
    assert "attachment" in response.headers.get("content-disposition", "") or "inline" in response.headers.get(
        "content-disposition", ""
    )


def test_reports_api_pdf_endpoint(audited_doc_and_findings):
    doc, _ = audited_doc_and_findings
    response = client.get(f"/api/reports/{doc.id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_reports_api_nonexistent_doc_404():
    response = client.get("/api/reports/doc-non-existent-999/summary")
    assert response.status_code == 404
