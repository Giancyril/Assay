import pytest
from backend.rules.starter_rules import STARTER_NDA_RULES, RuleType, Severity


def test_starter_nda_rules_count_and_uniqueness():
    assert len(STARTER_NDA_RULES) == 10
    codes = [r.code for r in STARTER_NDA_RULES]
    ids = [r.id for r in STARTER_NDA_RULES]
    assert len(set(codes)) == 10, "Rule codes must be unique"
    assert len(set(ids)) == 10, "Rule IDs must be unique"


def test_starter_nda_rules_types():
    rule_types = {r.rule_type for r in STARTER_NDA_RULES}
    assert RuleType.REQUIRED_CLAUSE in rule_types
    assert RuleType.PROHIBITED_TERM in rule_types
    assert RuleType.NUMERIC_THRESHOLD in rule_types


def test_deterministic_regex_on_prohibited_terms():
    import re
    rule_nda_05 = next(r for r in STARTER_NDA_RULES if r.code == "NDA-05")
    assert rule_nda_05.deterministic_regex is not None
    
    test_sample = "Recipient shall not directly or indirectly solicit any employee of Discloser."
    match = re.search(rule_nda_05.deterministic_regex, test_sample, re.IGNORECASE)
    assert match is not None
