from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RuleType(StrEnum):
    REQUIRED_CLAUSE = "required_clause"
    PROHIBITED_TERM = "prohibited_term"
    NUMERIC_THRESHOLD = "numeric_threshold"
    CONDITIONAL = "conditional"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(StrEnum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class ComplianceRule(BaseModel):
    id: str
    code: str
    name: str
    rule_set: str = "Standard Commercial NDA"
    version: str = "1.0.0"
    description: str
    rule_type: RuleType
    severity: Severity
    applicable_document_types: list[str] = Field(default_factory=lambda: ["NDA", "Confidentiality Agreement"])
    parameters: dict[str, Any] = Field(default_factory=dict)
    deterministic_regex: str | None = None
    guidance: str | None = None


STARTER_NDA_RULES: list[ComplianceRule] = [
    ComplianceRule(
        id="rule-nda-01",
        code="NDA-01",
        name="Standard Carve-outs & Exclusions Definition",
        description="Must contain standard confidentiality exceptions: information publicly known, already in recipient's possession prior to disclosure, independently developed without reference, or received rightfully from a third party.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.HIGH,
        parameters={
            "required_elements": [
                "publicly known or in public domain",
                "prior possession or already known",
                "independently developed",
                "rightfully received from third party",
            ]
        },
        guidance="Absence of standard carve-outs exposes recipient to unbounded liability for public knowledge.",
    ),
    ComplianceRule(
        id="rule-nda-02",
        code="NDA-02",
        name="Confidentiality Term & Duration Limit",
        description="Confidentiality obligations must have a definite expiry not exceeding 36 months (3 years) from disclosure. Perpetual duration is strictly prohibited.",
        rule_type=RuleType.NUMERIC_THRESHOLD,
        severity=Severity.HIGH,
        parameters={"max_duration_months": 36, "allow_perpetual": False},
        deterministic_regex=r"\b(in perpetuity|indefinite(ly)?|survive forever|without limitation in time)\b",
        guidance="Flag any perpetual duration as Violation. Mark term > 36 months as Violation.",
    ),
    ComplianceRule(
        id="rule-nda-03",
        code="NDA-03",
        name="Return or Destruction of Confidential Materials",
        description="Must permit certified destruction as an alternative to physical return, and must allow automated archival IT backups to be retained.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        parameters={"allow_destruction": True, "allow_archival_backup": True},
        guidance="Contracts that mandate solely physical return without destruction option or archival backup carveout cannot be fulfilled by modern IT systems.",
    ),
    ComplianceRule(
        id="rule-nda-04",
        code="NDA-04",
        name="Approved Governing Law & Exclusive Jurisdiction",
        description="Must designate an approved commercial governing jurisdiction (State of Delaware, State of New York, or England & Wales).",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.MEDIUM,
        parameters={"approved_jurisdictions": ["Delaware", "New York", "England and Wales", "California"]},
        guidance="If no governing law clause exists or an unusual jurisdiction is chosen, route to Needs Review.",
    ),
    ComplianceRule(
        id="rule-nda-05",
        code="NDA-05",
        name="Prohibition of Non-Solicitation Encroachment",
        description="Strict prohibition on employee or contractor non-solicitation clauses being embedded into standard preliminary NDAs.",
        rule_type=RuleType.PROHIBITED_TERM,
        severity=Severity.CRITICAL,
        parameters={
            "prohibited_terms": ["solicit", "hire any employee", "non-solicitation of personnel", "recruit or induce"]
        },
        deterministic_regex=r"\b(shall not (directly or indirectly )?(solicit|hire|recruit|entice away)|non-solicitation)\b",
        guidance="NDAs are for confidentiality only; non-solicitation restrictions belong strictly in definitive commercial agreements.",
    ),
    ComplianceRule(
        id="rule-nda-06",
        code="NDA-06",
        name="Permitted Compelled Disclosures / Court Orders",
        description="Must permit disclosure required by valid court order, subpoena, or governmental regulation, subject to prompt notice where legally permissible.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.HIGH,
        parameters={"requires_prompt_notice": True, "allows_protective_order_cooperation": True},
        guidance="Absence leaves party in contempt of court or in breach of agreement.",
    ),
    ComplianceRule(
        id="rule-nda-07",
        code="NDA-07",
        name="Standard of Care (Reasonable Care)",
        description="Recipient duty of care must be limited to reasonable care or the same degree of care as recipient exercises for its own confidential information of like nature.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.MEDIUM,
        parameters={
            "max_standard": "reasonable care",
            "prohibited_standards": ["highest possible care", "absolute protection", "guarantee security"],
        },
        deterministic_regex=r"\b(highest (possible|degree of) care|absolute(ly)? (secure|protect)|guarantee(s)? against (any|all) loss)\b",
        guidance="Reject clauses mandating 'highest care' or unconditional guarantee of non-disclosure.",
    ),
    ComplianceRule(
        id="rule-nda-08",
        code="NDA-08",
        name="Injunctive Relief & Equitable Remedies",
        description="Must acknowledge that monetary damages alone may be inadequate for breach, entitling non-breaching party to seek injunctive relief without posting bond.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        parameters={"allow_equitable_relief": True},
        guidance="Standard enforcement protection.",
    ),
    ComplianceRule(
        id="rule-nda-09",
        code="NDA-09",
        name="No Warranty / As-Is Information Disclosure",
        description="Discloser discloses information AS IS with no implied warranties of accuracy or completeness; recipient evaluates at its own risk.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        parameters={"requires_as_is": True},
        guidance="Standard disclaimer preventing claims of misrepresentation from preliminary discussions.",
    ),
    ComplianceRule(
        id="rule-nda-10",
        code="NDA-10",
        name="Prohibition of Non-Circumvent & Exclusivity",
        description="Prohibits non-circumvention, deal exclusivity, or lock-up covenants being included in standard mutual NDAs.",
        rule_type=RuleType.PROHIBITED_TERM,
        severity=Severity.HIGH,
        parameters={"prohibited_terms": ["non-circumvent", "non-circumvention", "exclusive negotiation", "lock-up"]},
        deterministic_regex=r"\b(non-circumvent(ion)?|exclusive negotiation|exclusivity period|lock-up)\b",
        guidance="NDAs must not inadvertently tie companies into exclusive business dealings.",
    ),
]
