import pytest
from fastapi.testclient import TestClient

from backend.agent.findings import Finding, findings_repository
from backend.app.main import app
from backend.benchmark.engine import RegulatoryCrosswalkEngine
from backend.benchmark.models import ComplianceStatusTier, RegulatoryStandard
from backend.ingestion.models import DocumentFileType, ParsedDocument
from backend.ingestion.repository import doc_repository
from backend.rules.models import RuleType, Severity, Verdict

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


def test_benchmark_engine_clean_document():
    doc = _make_dummy_doc("doc-clean-bench", "clean_vendor.pdf", "Full compliant text.")
    report = RegulatoryCrosswalkEngine.evaluate(document=doc, findings=[])

    assert report.global_compliance_index == 100.0
    assert len(report.crosswalk_matrix) == 0
    for standard, breakdown in report.standard_breakdowns.items():
        assert breakdown.tier == ComplianceStatusTier.COMPLIANT
        assert breakdown.score == 100.0
        assert len(breakdown.key_gaps) == 0


def test_benchmark_engine_multi_standard_crosswalk():
    doc = _make_dummy_doc("doc-risky-bench", "risky_vendor.pdf", "Risky clauses text.")
    findings = [
        Finding(
            id="f-bench-1",
            document_id="doc-risky-bench",
            rule_id="RULE-SEC-BREACH",
            rule_code="SEC-BREACH",
            rule_name="Missing 72-Hour Breach Notification",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.CRITICAL,
            reasoning="Vendor agreement omits the mandatory 72-hour security incident and breach notification.",
            recommended_action="Add GDPR Art 33 clause",
            confidence=0.95,
        ),
        Finding(
            id="f-bench-2",
            document_id="doc-risky-bench",
            rule_id="RULE-AUDIT-RIGHTS",
            rule_code="AUDIT-RIGHTS",
            rule_name="No Third-Party Audit Rights",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="Customer is denied right to conduct security audits or request SOC 2 reports.",
            recommended_action="Add audit clause",
            confidence=0.92,
        ),
        Finding(
            id="f-bench-3",
            document_id="doc-risky-bench",
            rule_id="RULE-SUBPROCESSOR",
            rule_code="SUBPROCESSOR",
            rule_name="Unilateral Subprocessor Engagement",
            rule_type=RuleType.PROHIBITED_TERM,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="Vendor permits subcontracting personal data processing without customer consent.",
            recommended_action="Require prior written consent",
            confidence=0.90,
        ),
    ]

    report = RegulatoryCrosswalkEngine.evaluate(document=doc, findings=findings)

    assert report.global_compliance_index < 100.0
    assert len(report.crosswalk_matrix) >= 2

    # Verify crosswalk citations
    breach_item = next(i for i in report.crosswalk_matrix if "breach" in i.rule_name.lower())
    assert RegulatoryStandard.GDPR in breach_item.affected_standards
    assert RegulatoryStandard.HIPAA in breach_item.affected_standards
    assert RegulatoryStandard.SOC2_TYPE2 in breach_item.affected_standards
    assert "Art. 33" in breach_item.citations["GDPR"]
    assert "164.404" in breach_item.citations["HIPAA"]

    # Check breakdowns reflect gaps
    gdpr_status = report.standard_breakdowns["GDPR"]
    assert gdpr_status.failed_requirements_count > 0
    assert gdpr_status.score < 100.0


def test_benchmark_api_catalog():
    res = client.get("/api/benchmark/standards/catalog")
    assert res.status_code == 200
    data = res.json()
    assert "GDPR" in data
    assert "HIPAA" in data
    assert "SOC2_TYPE2" in data
    assert "ISO27001" in data
    assert len(data["GDPR"]) >= 3


def test_benchmark_api_evaluate_and_get():
    doc_id = "doc-bench-api-test"
    doc = _make_dummy_doc(doc_id, "api_contract.pdf", "Some text.")
    doc_repository._memory_cache[doc.id] = doc

    findings = [
        Finding(
            id="f-api-bench-1",
            document_id=doc_id,
            rule_id="RULE-AUDIT-01",
            rule_code="AUDIT-01",
            rule_name="Missing Audit Rights",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="Audit inspection clause missing.",
            recommended_action="Add audit clause",
            confidence=0.90,
        )
    ]
    findings_repository.save_findings(doc_id, findings)

    # POST evaluate
    res = client.post(f"/api/benchmark/evaluate/{doc_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    assert "global_compliance_index" in data
    assert "standard_breakdowns" in data
    assert "crosswalk_matrix" in data

    # GET retrieve
    get_res = client.get(f"/api/benchmark/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["report_id"] == data["report_id"]


def test_benchmark_api_not_found():
    res = client.post("/api/benchmark/evaluate/non-existent-doc-id-000")
    assert res.status_code == 404
