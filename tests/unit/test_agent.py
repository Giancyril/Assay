import pytest
from fastapi.testclient import TestClient

from backend.agent.graph import compliance_graph
from backend.agent.orchestrator import check_document_against_ruleset
from backend.agent.state import ComplianceCheckState
from backend.app.main import app
from backend.ingestion.service import ingest_document_bytes
from backend.rules.engine import rule_engine
from backend.rules.models import Verdict

client = TestClient(app)

TEST_AUDIT_DOC = """MUTUAL NON-DISCLOSURE AGREEMENT
Effective October 12, 2026.

1. DEFINITIONS AND EXCLUSIONS.
Confidential Information shall not include information that: (a) is or becomes publicly known;
(b) was already in Recipient's possession prior to disclosure; or (c) is independently developed.

2. STANDARD OF CARE.
Recipient agrees to exercise reasonable care to maintain confidentiality of Discloser's information.

3. TERM AND DURATION.
The confidentiality obligations set forth herein shall survive termination of this Agreement and continue in perpetuity.

4. RETURN OF MATERIALS.
Upon written request, Recipient shall promptly return or certify destruction of all Confidential Information, provided that archival IT backups may be retained.

5. COMPELLED DISCLOSURES.
Recipient may disclose Confidential Information pursuant to a valid subpoena or court order, provided prompt written notice is provided.

6. GOVERNING LAW.
This Agreement shall be governed by the laws of the State of Delaware.

7. INJUNCTIVE RELIEF.
Breach may cause irreparable harm for which damages are inadequate, entitling Discloser to seek injunctive relief without bond.

8. PROHIBITED PERSONNEL COVENANT.
Recipient agrees that during the term of this Agreement and for eighteen (18) months thereafter, Recipient shall not directly or indirectly solicit, recruit, or hire any officer or employee of Discloser.
"""

def create_audit_test_doc():
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    rect = pymupdf.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, TEST_AUDIT_DOC, fontsize=8)
    pdf_bytes = doc.tobytes()
    doc.close()
    return ingest_document_bytes(pdf_bytes, "test_agent_audit.pdf")


def test_agent_graph_execution_on_prohibited_solicitation():
    doc = create_audit_test_doc()
    nda_set = rule_engine.get_rule_set("ruleset-nda-commercial")
    rule_nda_05 = next(r for r in nda_set.rules if r.code == "NDA-05")

    state = ComplianceCheckState(
        document_id=doc.id,
        rule_id=rule_nda_05.id,
        rule=rule_nda_05,
        full_document_text=doc.full_text
    )

    result = compliance_graph.invoke(state)
    assert result["verdict"] == Verdict.VIOLATION
    assert result["evidence_verified"] is True
    assert "solicit" in result["verbatim_quote"].lower()
    assert result["page_number"] == 1
    assert result["char_start"] is not None


def test_agent_graph_execution_on_perpetual_term():
    doc = create_audit_test_doc()
    nda_set = rule_engine.get_rule_set("ruleset-nda-commercial")
    rule_nda_02 = next(r for r in nda_set.rules if r.code == "NDA-02")

    state = ComplianceCheckState(
        document_id=doc.id,
        rule_id=rule_nda_02.id,
        rule=rule_nda_02,
        full_document_text=doc.full_text
    )

    result = compliance_graph.invoke(state)
    assert result["verdict"] == Verdict.VIOLATION
    assert result["evidence_verified"] is True
    assert "perpetuity" in result["verbatim_quote"].lower()


def test_agent_graph_execution_on_compliant_governing_law():
    doc = create_audit_test_doc()
    nda_set = rule_engine.get_rule_set("ruleset-nda-commercial")
    rule_nda_04 = next(r for r in nda_set.rules if r.code == "NDA-04")

    state = ComplianceCheckState(
        document_id=doc.id,
        rule_id=rule_nda_04.id,
        rule=rule_nda_04,
        full_document_text=doc.full_text
    )

    result = compliance_graph.invoke(state)
    assert result["verdict"] == Verdict.COMPLIANT
    assert result["evidence_verified"] is True
    assert "Delaware" in result["verbatim_quote"]


def test_searches_recorded_for_multi_phrasing_absence():
    doc = create_audit_test_doc()
    nda_set = rule_engine.get_rule_set("ruleset-nda-commercial")
    rule_nda_09 = next(r for r in nda_set.rules if r.code == "NDA-09")  # As-Is disclaimer

    state = ComplianceCheckState(
        document_id=doc.id,
        rule_id=rule_nda_09.id,
        rule=rule_nda_09,
        full_document_text=doc.full_text
    )

    result = compliance_graph.invoke(state)
    assert len(result["searches_run"]) >= 1
    assert any("hybrid_search" in s for s in result["searches_run"])


@pytest.mark.asyncio
async def test_parallel_document_orchestrator():
    doc = create_audit_test_doc()
    findings = await check_document_against_ruleset(
        document_id=doc.id,
        ruleset_id="ruleset-nda-commercial",
        max_concurrency=4
    )

    assert len(findings) == 10
    violations = [f for f in findings if f.verdict == Verdict.VIOLATION]
    # NDA-02 (perpetual term) and NDA-05 (solicitation) must be caught as violations
    violation_codes = {v.rule_code for v in violations}
    assert "NDA-02" in violation_codes
    assert "NDA-05" in violation_codes


def test_checks_api_roundtrip():
    doc = create_audit_test_doc()

    # 1. Run check
    response = client.post(
        "/api/checks/run",
        json={"document_id": doc.id, "ruleset_id": "ruleset-nda-commercial"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_findings"] == 10
    assert data["counts"]["violation"] >= 2

    # 2. Get findings
    get_res = client.get(f"/api/checks/{doc.id}/findings")
    assert get_res.status_code == 200
    assert len(get_res.json()) == 10

    # 3. Get single finding
    first_id = get_res.json()[0]["id"]
    single_res = client.get(f"/api/checks/findings/{first_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == first_id
