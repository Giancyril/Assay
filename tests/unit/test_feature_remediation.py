from fastapi.testclient import TestClient

from backend.agent.findings import Finding, findings_repository
from backend.app.main import app
from backend.ingestion.models import DocumentFileType, ParsedDocument
from backend.ingestion.repository import doc_repository
from backend.remediation.engine import RemediationPlaybookEngine
from backend.remediation.models import (
    RemediationActionType,
    RemediationStatus,
)
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


def test_remediation_engine_generates_action_items():
    engine = RemediationPlaybookEngine()
    findings = [
        Finding(
            id="f-1",
            document_id="doc-rem-1",
            rule_id="RULE-CONF-001",
            rule_code="CONF-001",
            rule_name="Perpetual Confidentiality Clause",
            rule_type=RuleType.PROHIBITED_TERM,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="The agreement imposes indefinite confidentiality obligations without term limits.",
            recommended_action="Limit term to 3 years",
            confidence=0.95,
        ),
        Finding(
            id="f-2",
            document_id="doc-rem-1",
            rule_id="RULE-LIAB-001",
            rule_code="LIAB-001",
            rule_name="Uncapped Liability and Indemnification",
            rule_type=RuleType.NUMERIC_THRESHOLD,
            verdict=Verdict.VIOLATION,
            severity=Severity.CRITICAL,
            reasoning="Agreement exposes customer to unlimited liability with no dollar cap.",
            recommended_action="Cap at 12 months fees",
            confidence=0.98,
        ),
        Finding(
            id="f-3",
            document_id="doc-rem-1",
            rule_id="RULE-SEC-001",
            rule_code="SEC-001",
            rule_name="Breach Notification Protocol",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.NEEDS_REVIEW,
            severity=Severity.HIGH,
            reasoning="Missing mandatory 72-hour security incident and breach notification mechanism.",
            recommended_action="Add 72 hour breach notification",
            confidence=0.90,
        ),
        Finding(
            id="f-4",
            document_id="doc-rem-1",
            rule_id="RULE-AUDIT-001",
            rule_code="AUDIT-001",
            rule_name="Right to Audit",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.MEDIUM,
            reasoning="No contractual inspection or audit rights guaranteed.",
            recommended_action="Insert audit clause",
            confidence=0.92,
        ),
        Finding(
            id="f-5",
            document_id="doc-rem-1",
            rule_id="RULE-PASS-001",
            rule_code="PASS-001",
            rule_name="Governing Law",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.COMPLIANT,
            severity=Severity.LOW,
            reasoning="Governing law clause is acceptable.",
            recommended_action="None required",
            confidence=0.99,
        ),
    ]

    doc = _make_dummy_doc("doc-rem-1", "contract.pdf", "Sample contract text.")
    playbook = engine.generate_playbook(
        document_id="doc-rem-1",
        findings=findings,
        parsed_doc=doc,
        target_completion_days=30,
    )

    # 4 non-compliant findings should generate 4 action items
    assert playbook.total_actions == 4
    assert playbook.critical_actions_count >= 1
    assert playbook.high_actions_count >= 1
    assert len(playbook.items) == 4

    # Check suggested clauses exist
    types = [item.action_type for item in playbook.items]
    assert RemediationActionType.CONTRACT_AMENDMENT in types
    assert RemediationActionType.TECHNICAL_CONTROL in types
    assert RemediationActionType.VENDOR_NEGOTIATION in types

    # Check clause text provided for amendments
    amendments = [i for i in playbook.items if i.action_type == RemediationActionType.CONTRACT_AMENDMENT]
    assert len(amendments) >= 1
    assert amendments[0].suggested_clause is not None
    assert len(amendments[0].suggested_clause) > 20


def test_remediation_action_status_lifecycle():
    engine = RemediationPlaybookEngine()
    findings = [
        Finding(
            id="f-liab",
            document_id="doc-rem-2",
            rule_id="RULE-LIAB-001",
            rule_code="LIAB-001",
            rule_name="Uncapped Liability",
            rule_type=RuleType.NUMERIC_THRESHOLD,
            verdict=Verdict.VIOLATION,
            severity=Severity.CRITICAL,
            reasoning="Unlimited indemnity exposures.",
            recommended_action="Cap liability",
            confidence=0.95,
        )
    ]
    doc = _make_dummy_doc("doc-rem-2", "saas_agreement.pdf", "Contract text.")
    playbook = engine.generate_playbook("doc-rem-2", findings, doc)

    item = playbook.items[0]
    assert item.status == RemediationStatus.PENDING

    # Transition to IN_PROGRESS
    updated = engine.update_action_status(
        playbook_id=playbook.playbook_id,
        action_id=item.action_id,
        new_status=RemediationStatus.IN_PROGRESS,
        notes="Outside counsel retained for negotiation.",
    )
    assert updated is not None
    assert updated.status == RemediationStatus.IN_PROGRESS
    assert "Outside counsel" in updated.description

    # Transition to RESOLVED
    resolved = engine.update_action_status(
        playbook_id=playbook.playbook_id,
        action_id=item.action_id,
        new_status=RemediationStatus.RESOLVED,
    )
    assert resolved.status == RemediationStatus.RESOLVED
    assert resolved.completed_at is not None


def test_remediation_api_workflow():
    doc_id = "doc-api-rem-1"
    doc = _make_dummy_doc(doc_id, "vendor_contract.pdf", "Vendor contract sample.")
    doc_repository._memory_cache[doc.id] = doc

    findings = [
        Finding(
            id="f-api-1",
            document_id=doc_id,
            rule_id="RULE-SEC-72H",
            rule_code="SEC-72H",
            rule_name="72h Data Breach Notification Missing",
            rule_type=RuleType.REQUIRED_CLAUSE,
            verdict=Verdict.VIOLATION,
            severity=Severity.HIGH,
            reasoning="Requires 72 hour breach notification SLA.",
            recommended_action="Insert breach clause",
            confidence=0.95,
        )
    ]
    findings_repository.save_findings(doc_id, findings)

    # 1. Generate playbook
    resp = client.post("/api/remediation/generate", json={"document_id": doc_id, "target_completion_days": 21})
    assert resp.status_code == 201
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["total_actions"] == 1
    playbook_id = data["playbook_id"]
    action_id = data["items"][0]["action_id"]

    # 2. Get by playbook id
    resp_get = client.get(f"/api/remediation/{playbook_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["playbook_id"] == playbook_id

    # 3. Get by document id
    resp_doc = client.get(f"/api/remediation/document/{doc_id}")
    assert resp_doc.status_code == 200
    assert resp_doc.json()["document_id"] == doc_id

    # 4. Update action status
    resp_patch = client.patch(
        f"/api/remediation/{playbook_id}/action/{action_id}",
        json={"status": "RESOLVED", "notes": "Addendum signed by vendor."},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["status"] == "RESOLVED"
    assert resp_patch.json()["completed_at"] is not None


def test_remediation_api_not_found():
    resp = client.post("/api/remediation/generate", json={"document_id": "non-existent-doc"})
    assert resp.status_code == 404

    resp2 = client.get("/api/remediation/non-existent-playbook")
    assert resp2.status_code == 404
