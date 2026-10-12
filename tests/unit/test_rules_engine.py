import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.rules.engine import rule_engine
from backend.rules.models import Verdict, RuleType, Severity, ComplianceRule, RuleParameters
from backend.rules.precheck import run_deterministic_precheck

client = TestClient(app)


def test_starter_rule_sets_loaded():
    sets = rule_engine.list_rule_sets()
    assert len(sets) >= 2
    nda_set = rule_engine.get_rule_set("ruleset-nda-commercial")
    assert nda_set.version == "1.0.0"
    assert len(nda_set.rules) == 10

    hygiene_set = rule_engine.get_rule_set("ruleset-contract-hygiene")
    assert hygiene_set.version == "1.0.0"
    assert len(hygiene_set.rules) == 6


def test_rule_set_versioning_immutability():
    nda_v1 = rule_engine.get_rule_set("ruleset-nda-commercial", "1.0.0")
    original_rule_count = len(nda_v1.rules)

    # Create new version 1.1.0 with an extra rule
    new_rule = ComplianceRule(
        id="rule-nda-11-custom",
        code="NDA-11",
        name="Custom Whitelist Rule",
        rule_set_id="ruleset-nda-commercial",
        version="1.1.0",
        description="Custom rule in v1.1.0",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW
    )
    updated_rules = list(nda_v1.rules) + [new_rule]

    nda_v2 = rule_engine.create_new_version(
        ruleset_id="ruleset-nda-commercial",
        new_version="1.1.0",
        updated_rules=updated_rules,
        description="Minor update adding NDA-11"
    )

    assert nda_v2.version == "1.1.0"
    assert len(nda_v2.rules) == original_rule_count + 1

    # Verify version 1.0.0 remains intact
    nda_v1_recheck = rule_engine.get_rule_set("ruleset-nda-commercial", "1.0.0")
    assert nda_v1_recheck.version == "1.0.0"
    assert len(nda_v1_recheck.rules) == original_rule_count

    # Verify latest returns 1.1.0
    latest = rule_engine.get_rule_set("ruleset-nda-commercial")
    assert latest.version == "1.1.0"


def test_deterministic_prohibited_terms_precheck():
    rule_nda_05 = rule_engine.get_rule_set("ruleset-nda-commercial", "1.0.0").rules[4]
    assert rule_nda_05.code == "NDA-05"

    text = "Section 8. Recipient shall not directly or indirectly solicit or hire any employee of Discloser for two years."
    result = run_deterministic_precheck(text, rule_nda_05)

    assert result.has_deterministic_verdict is True
    assert result.verdict == Verdict.VIOLATION
    assert result.confidence == 1.0
    assert "solicit" in result.evidence_quote.lower()


def test_deterministic_perpetual_term_precheck():
    rule_nda_02 = rule_engine.get_rule_set("ruleset-nda-commercial", "1.0.0").rules[1]
    assert rule_nda_02.code == "NDA-02"

    text = "3. TERM. The confidentiality obligations set forth herein shall survive termination and continue in perpetuity."
    result = run_deterministic_precheck(text, rule_nda_02)

    assert result.has_deterministic_verdict is True
    assert result.verdict == Verdict.VIOLATION
    assert result.confidence == 1.0
    assert "perpetuity" in result.evidence_quote.lower()


def test_deterministic_numeric_duration_precheck():
    rule_nda_02 = rule_engine.get_rule_set("ruleset-nda-commercial", "1.0.0").rules[1]

    # Test 5 years (60 months) > 36 months cap -> VIOLATION
    violation_text = "The obligations of confidentiality shall remain in effect for a period of five (5) years from disclosure."
    v_res = run_deterministic_precheck(violation_text, rule_nda_02)
    assert v_res.has_deterministic_verdict is True
    assert v_res.verdict == Verdict.VIOLATION
    assert "exceeds" in v_res.reasoning.lower()

    # Test 2 years (24 months) <= 36 months cap -> COMPLIANT
    compliant_text = "The obligations of confidentiality shall expire two (2) years from the date of disclosure."
    c_res = run_deterministic_precheck(compliant_text, rule_nda_02)
    assert c_res.has_deterministic_verdict is True
    assert c_res.verdict == Verdict.COMPLIANT


def test_deterministic_notice_period_precheck():
    hygiene_set = rule_engine.get_rule_set("ruleset-contract-hygiene", "1.0.0")
    rule_hyg_02 = next(r for r in hygiene_set.rules if r.code == "HYG-02")

    # 15 days notice < 30 days minimum -> VIOLATION
    violation_text = "Either party may terminate this agreement upon fifteen (15) days written notice."
    v_res = run_deterministic_precheck(violation_text, rule_hyg_02)
    assert v_res.has_deterministic_verdict is True
    assert v_res.verdict == Verdict.VIOLATION
    assert "below required minimum" in v_res.reasoning.lower()

    # 60 days notice >= 30 days minimum -> COMPLIANT
    compliant_text = "Either party may terminate this agreement upon sixty (60) days prior written notice."
    c_res = run_deterministic_precheck(compliant_text, rule_hyg_02)
    assert c_res.has_deterministic_verdict is True
    assert c_res.verdict == Verdict.COMPLIANT


def test_rules_api_endpoints():
    # 1. List sets
    res = client.get("/api/rules/sets")
    assert res.status_code == 200
    sets = res.json()
    assert len(sets) >= 2

    # 2. Get specific set
    res2 = client.get("/api/rules/sets/ruleset-nda-commercial")
    assert res2.status_code == 200
    assert res2.json()["id"] == "ruleset-nda-commercial"

    # 3. Precheck API
    precheck_res = client.post(
        "/api/rules/precheck",
        json={
            "candidate_text": "Recipient shall not solicit any employee.",
            "rule_id": "NDA-05",
            "ruleset_id": "ruleset-nda-commercial"
        }
    )
    assert precheck_res.status_code == 200
    data = precheck_res.json()
    assert data["has_deterministic_verdict"] is True
    assert data["verdict"] == "violation"
