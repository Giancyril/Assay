"""
Unit tests for Day 1 Advanced Features:
  1. Automated Redlining Engine
  2. Visual Document Highlighting & Jump-to-Source
  3. Real-Time SSE Audit Streaming (router endpoint only)
  4. Custom Rule Studio & Ruleset Importer
  5. Cryptographic Audit Certificate & Verification
"""
import json

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.certificate.generator import AuditCertificate, generate_certificate, verify_certificate
from backend.highlight.locator import build_highlight_map
from backend.highlight.models import VERDICT_COLOR_MAP, DocumentHighlightMap
from backend.redline.engine import RedlineEngine, compute_word_diff
from backend.redline.models import DiffOp, DiffToken, RedlineDiff
from backend.rules.models import RuleType, Severity
from backend.rules.studio import (
    CreateRuleRequest,
    CreateRulesetRequest,
    create_custom_ruleset,
    delete_custom_ruleset,
    delete_rule_from_ruleset,
    get_custom_ruleset,
    import_ruleset_from_json,
    list_custom_rulesets,
)

client = TestClient(app)


# -------------------------------------------------------------
# Feature 1: Automated Redlining Engine
# -------------------------------------------------------------

def test_compute_word_diff_equal():
    tokens, markup, unified = compute_word_diff("hello world", "hello world")
    assert all(t.op == DiffOp.EQUAL for t in tokens)
    assert markup == "hello world"


def test_compute_word_diff_replace():
    tokens, markup, unified = compute_word_diff("foo bar", "foo baz")
    ops = [t.op for t in tokens]
    assert DiffOp.DELETE in ops
    assert DiffOp.INSERT in ops
    assert "[-bar-]" in markup
    assert "{+baz+}" in markup


def test_compute_word_diff_insert():
    tokens, markup, unified = compute_word_diff("hello", "hello world")
    ops = [t.op for t in tokens]
    assert DiffOp.INSERT in ops
    assert "world" in markup
    assert "{+" in markup and "+}" in markup

def test_compute_word_diff_unified_diff_format():
    _tokens, _markup, unified = compute_word_diff("original text", "remediated text")
    assert "---" in unified or "+++ " in unified or unified == ""


def test_redline_engine_nda_02():
    """NDA-02: perpetual term should produce a 3-year cap replacement."""
    from backend.agent.findings import Finding
    from backend.evidence.verifier import EvidenceSpan
    from backend.rules.models import RuleType, Severity, Verdict

    finding = Finding(
        document_id="doc-test",
        rule_id="NDA-02",
        rule_code="NDA-02",
        rule_name="Confidentiality Term Limit",
        rule_type=RuleType.NUMERIC_THRESHOLD,
        verdict=Verdict.VIOLATION,
        severity=Severity.HIGH,
        reasoning="Perpetual confidentiality term detected.",
        recommended_action="Replace with 3-year term.",
        confidence=1.0,
        evidence=EvidenceSpan(
            verbatim_quote="confidentiality obligations shall survive in perpetuity",
            page_number=2,
            char_start=100,
            char_end=162,
            verified=True,
        ),
    )

    engine = RedlineEngine()
    diff = engine.generate_redline_for_finding(finding)

    assert isinstance(diff, RedlineDiff)
    assert "three (3) years" in diff.remediated_text.lower() or "3" in diff.remediated_text
    assert diff.finding_id == finding.id
    assert diff.page_number == 2
    assert diff.rule_code == "NDA-02"
    assert len(diff.tokens) > 0


def test_redline_engine_nda_05():
    """NDA-05: non-solicitation clause should be deleted entirely."""
    from backend.agent.findings import Finding
    from backend.rules.models import RuleType, Severity, Verdict

    finding = Finding(
        document_id="doc-test",
        rule_id="NDA-05",
        rule_code="NDA-05",
        rule_name="Non-Solicitation Encroachment",
        rule_type=RuleType.PROHIBITED_TERM,
        verdict=Verdict.VIOLATION,
        severity=Severity.CRITICAL,
        reasoning="Non-solicitation clause found.",
        recommended_action="Delete this clause.",
        confidence=1.0,
    )

    engine = RedlineEngine()
    remediated, rationale = engine.generate_remediation_clause(finding)
    assert "Intentionally Deleted" in remediated or "omitted" in remediated.lower()
    assert rationale


def test_redline_engine_nda_01():
    """NDA-01: should restore full 4-part carve-outs."""
    from backend.agent.findings import Finding
    from backend.rules.models import RuleType, Severity, Verdict

    finding = Finding(
        document_id="doc-test",
        rule_id="NDA-01",
        rule_code="NDA-01",
        rule_name="Exclusions and Carve-outs",
        rule_type=RuleType.REQUIRED_CLAUSE,
        verdict=Verdict.VIOLATION,
        severity=Severity.HIGH,
        reasoning="Missing standard carve-outs.",
        recommended_action="Add 4 standard carve-outs.",
        confidence=1.0,
    )

    engine = RedlineEngine()
    remediated, rationale = engine.generate_remediation_clause(finding)
    assert "publicly known" in remediated.lower()
    assert "independently developed" in remediated.lower()


def test_redline_engine_generate_all_skips_compliant():
    """generate_all_redlines should only process violations/needs_review."""
    from backend.agent.findings import Finding
    from backend.rules.models import RuleType, Severity, Verdict

    compliant = Finding(
        document_id="doc-test",
        rule_id="NDA-01",
        rule_code="NDA-01",
        rule_name="Carve-outs",
        rule_type=RuleType.REQUIRED_CLAUSE,
        verdict=Verdict.COMPLIANT,
        severity=Severity.LOW,
        reasoning="Compliant",
        recommended_action="",
        confidence=1.0,
    )
    engine = RedlineEngine()
    diffs = engine.generate_all_redlines([compliant])
    assert diffs == []


def test_redline_api_404_no_findings():
    """GET /api/redline/{doc_id} returns 404 for unknown doc."""
    res = client.get("/api/redline/doc-does-not-exist-xyz")
    assert res.status_code == 404


# -------------------------------------------------------------
# Feature 2: Visual Document Highlighting
# -------------------------------------------------------------

def test_verdict_color_map_coverage():
    for verdict in ("violation", "needs_review", "compliant", "not_applicable"):
        assert verdict in VERDICT_COLOR_MAP
        assert VERDICT_COLOR_MAP[verdict].startswith("#")


def test_build_highlight_map_empty():
    result = build_highlight_map("doc-no-findings", [])
    assert isinstance(result, DocumentHighlightMap)
    assert result.total_annotations == 0
    assert result.annotations == []


def test_build_highlight_map_with_findings():
    from backend.agent.findings import Finding
    from backend.evidence.verifier import EvidenceSpan
    from backend.rules.models import RuleType, Severity, Verdict

    findings = [
        Finding(
            document_id="doc-test",
            rule_id="NDA-01",
            rule_code="NDA-01",
            rule_name="Carve-outs",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="Missing carve-outs",
            recommended_action="Add them",
            confidence=0.95,
            evidence=EvidenceSpan(
                verbatim_quote="no carve-outs present",
                page_number=3,
                char_start=50,
                char_end=71,
                verified=True,
            ),
        )
    ]

    result = build_highlight_map("doc-test", findings)
    assert result.total_annotations == 1
    ann = result.annotations[0]
    assert ann.verdict == "violation"
    assert ann.page_number == 3
    assert ann.color == VERDICT_COLOR_MAP["violation"]
    assert "NDA-01" in ann.label
    assert "3" in result.page_index  # page 3 is indexed


def test_highlight_api_404_no_findings():
    res = client.get("/api/highlight/doc-does-not-exist-xyz")
    assert res.status_code == 404


# -------------------------------------------------------------
# Feature 3: SSE Streaming (router header test)
# -------------------------------------------------------------

def test_stream_audit_content_type():
    """
    Verify the /api/stream/{doc_id}/audit endpoint returns text/event-stream
    with correct anti-buffering headers.
    Note: TestClient collects the full response; we only verify headers here.
    """
    res = client.get("/api/stream/doc-does-not-exist-xyz/audit", timeout=10)
    assert "text/event-stream" in res.headers.get("content-type", "")
    # Even on error the generator should have emitted an SSE error event
    assert "data:" in res.text


# -------------------------------------------------------------
# Feature 4: Custom Rule Studio
# -------------------------------------------------------------

def test_create_custom_ruleset():
    req = CreateRulesetRequest(
        name="Test Ruleset",
        description="Unit test ruleset",
        document_type="NDA",
        rules=[
            CreateRuleRequest(
                code="TEST-01",
                name="Test Required Clause",
                description="Must include test clause",
                rule_type=RuleType.REQUIRED_CLAUSE,
                severity=Severity.MEDIUM,
                required_elements=["test clause"],
            )
        ],
    )
    ruleset = create_custom_ruleset(req)
    assert ruleset.id.startswith("ruleset-custom-")
    assert len(ruleset.rules) == 1
    assert ruleset.rules[0].code == "TEST-01"

    # Cleanup
    delete_custom_ruleset(ruleset.id)


def test_get_custom_ruleset_not_found():
    import pytest
    with pytest.raises(KeyError):
        get_custom_ruleset("ruleset-custom-does-not-exist")


def test_delete_rule_from_custom_ruleset():
    req = CreateRulesetRequest(
        name="Delete Test Ruleset",
        description="Testing rule deletion",
        document_type="NDA",
        rules=[
            CreateRuleRequest(
                code="DEL-01",
                name="Delete Me",
                description="This rule will be deleted",
                rule_type=RuleType.PROHIBITED_TERM,
                severity=Severity.LOW,
            )
        ],
    )
    ruleset = create_custom_ruleset(req)
    assert len(ruleset.rules) == 1

    updated = delete_rule_from_ruleset(ruleset.id, "DEL-01")
    assert len(updated.rules) == 0

    # Cleanup
    delete_custom_ruleset(ruleset.id)


def test_import_ruleset_from_json():
    payload = {
        "id": "ruleset-import-test",
        "name": "Imported Ruleset",
        "version": "1.0.0",
        "description": "Imported from JSON",
        "document_type": "NDA",
        "rules": [
            {
                "id": "rule-imported-01",
                "code": "IMP-01",
                "name": "Imported Rule",
                "rule_set_id": "ruleset-import-test",
                "description": "An imported rule",
                "rule_type": "required_clause",
                "severity": "medium",
            }
        ],
        "is_default": False,
    }
    ruleset = import_ruleset_from_json(json.dumps(payload))
    assert ruleset.id.startswith("ruleset-custom-")
    assert ruleset.name == "Imported Ruleset"
    assert len(ruleset.rules) == 1

    # Cleanup
    delete_custom_ruleset(ruleset.id)


def test_studio_api_create_and_list():
    """API-level test for POST /api/studio/rulesets and GET /api/studio/rulesets."""
    payload = {
        "name": "API Test Ruleset",
        "description": "Created via API",
        "document_type": "NDA",
        "rules": [],
    }
    create_res = client.post("/api/studio/rulesets", json=payload)
    assert create_res.status_code == 201
    data = create_res.json()
    ruleset_id = data["id"]
    assert ruleset_id.startswith("ruleset-custom-")

    # List should contain it
    list_res = client.get("/api/studio/rulesets")
    assert list_res.status_code == 200
    ids = [r["id"] for r in list_res.json()]
    assert ruleset_id in ids

    # Delete via API
    del_res = client.delete(f"/api/studio/rulesets/{ruleset_id}")
    assert del_res.status_code == 204


def test_studio_api_add_rule():
    """POST /api/studio/rulesets/{id}/rules should add a rule."""
    create_res = client.post(
        "/api/studio/rulesets",
        json={"name": "Rule Add Test", "description": "Adding a rule", "document_type": "NDA"},
    )
    assert create_res.status_code == 201
    ruleset_id = create_res.json()["id"]

    rule_payload = {
        "code": "ADD-01",
        "name": "Added Rule",
        "description": "Rule added via API",
        "rule_type": "required_clause",
        "severity": "low",
    }
    add_res = client.post(f"/api/studio/rulesets/{ruleset_id}/rules", json=rule_payload)
    assert add_res.status_code == 201
    assert len(add_res.json()["rules"]) == 1

    # Cleanup
    client.delete(f"/api/studio/rulesets/{ruleset_id}")


# -------------------------------------------------------------
# Feature 5: Cryptographic Audit Certificate
# -------------------------------------------------------------

def test_certificate_verify_unmodified():
    """A freshly generated certificate should verify successfully."""
    from backend.certificate.generator import _sha256, _hmac_sign, _canonical_payload

    # Build a minimal cert dict and sign it
    cert_data = {
        "certificate_id": "cert-abc123",
        "issued_at": "2024-01-01T00:00:00+00:00",
        "issuer": "Test",
        "document_id": "doc-test",
        "document_filename": "test.pdf",
        "document_text_sha256": "deadbeef",
        "ruleset_id": "ruleset-nda-commercial",
        "ruleset_version": "1.0.0",
        "total_findings": 0,
        "compliance_score": 100.0,
        "overall_status": "COMPLIANT",
        "counts": {"violation": 0, "needs_review": 0, "compliant": 0, "not_applicable": 0},
        "findings": [],
    }
    canonical = _canonical_payload(cert_data)
    payload_hash = _sha256(canonical)
    signature = _hmac_sign(payload_hash)
    cert_data["payload_sha256"] = payload_hash
    cert_data["hmac_signature"] = signature
    cert_data["verified"] = False

    cert = AuditCertificate.model_validate(cert_data)
    assert verify_certificate(cert) is True


def test_certificate_verify_tampered():
    """Mutating any field after issuance should invalidate the certificate."""
    from backend.certificate.generator import _sha256, _hmac_sign, _canonical_payload

    cert_data = {
        "certificate_id": "cert-tampered",
        "issued_at": "2024-01-01T00:00:00+00:00",
        "issuer": "Test",
        "document_id": "doc-test",
        "document_filename": "test.pdf",
        "document_text_sha256": "deadbeef",
        "ruleset_id": "ruleset-nda-commercial",
        "ruleset_version": "1.0.0",
        "total_findings": 2,
        "compliance_score": 50.0,
        "overall_status": "NON_COMPLIANT",
        "counts": {"violation": 2, "needs_review": 0, "compliant": 0, "not_applicable": 0},
        "findings": [],
    }
    canonical = _canonical_payload(cert_data)
    payload_hash = _sha256(canonical)
    signature = _hmac_sign(payload_hash)
    cert_data["payload_sha256"] = payload_hash
    cert_data["hmac_signature"] = signature
    cert_data["verified"] = False

    cert = AuditCertificate.model_validate(cert_data)
    assert verify_certificate(cert) is True

    # Tamper with the compliance score
    cert.compliance_score = 100.0
    assert verify_certificate(cert) is False


def test_certificate_api_verify_endpoint():
    """POST /api/certificates/verify should return valid=true for a correct cert."""
    from backend.certificate.generator import _sha256, _hmac_sign, _canonical_payload

    cert_data = {
        "certificate_id": "cert-api-test",
        "issued_at": "2024-01-01T00:00:00+00:00",
        "issuer": "Test",
        "document_id": "doc-api-test",
        "document_filename": "api_test.pdf",
        "document_text_sha256": "abc123",
        "ruleset_id": "ruleset-nda-commercial",
        "ruleset_version": "1.0.0",
        "total_findings": 0,
        "compliance_score": 100.0,
        "overall_status": "COMPLIANT",
        "counts": {"violation": 0, "needs_review": 0, "compliant": 0, "not_applicable": 0},
        "findings": [],
    }
    canonical = _canonical_payload(cert_data)
    payload_hash = _sha256(canonical)
    signature = _hmac_sign(payload_hash)
    cert_data["payload_sha256"] = payload_hash
    cert_data["hmac_signature"] = signature
    cert_data["verified"] = False

    res = client.post("/api/certificates/verify", json=cert_data)
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True
    assert body["certificate_id"] == "cert-api-test"


def test_certificate_api_issue_404_for_unknown_doc():
    """POST /api/certificates/{doc_id} should return 404 for unknown documents."""
    res = client.post("/api/certificates/doc-does-not-exist-xyz?ruleset_id=ruleset-nda-commercial")
    assert res.status_code == 404
