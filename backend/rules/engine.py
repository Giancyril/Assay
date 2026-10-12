from fastapi import HTTPException, status

from backend.rules.models import (
    ComplianceRule,
    RuleParameters,
    RuleSet,
    RuleType,
    Severity,
)

# ----------------- STARTER RULE SET: COMMERCIAL NDA -----------------
STARTER_NDA_RULES = [
    ComplianceRule(
        id="rule-nda-01",
        code="NDA-01",
        name="Standard Carve-outs & Exclusions Definition",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Must contain standard confidentiality exceptions: publicly known, prior possession, independently developed, and rightful receipt from third party.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.HIGH,
        applicable_document_types=["NDA", "Confidentiality Agreement"],
        parameters=RuleParameters(
            required_elements=[
                "publicly known",
                "prior possession",
                "independently developed",
                "rightfully received"
            ]
        ),
        search_queries=[
            "confidential information shall not include exceptions",
            "carve-outs publicly known prior possession independently developed",
            "exclusions to confidential information"
        ],
        guidance="Absence of standard carve-outs leaves recipient with unbounded liability."
    ),
    ComplianceRule(
        id="rule-nda-02",
        code="NDA-02",
        name="Confidentiality Term & Duration Limit",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Confidentiality obligations must have a definite expiry not exceeding 36 months (3 years). Perpetual duration is strictly prohibited.",
        rule_type=RuleType.NUMERIC_THRESHOLD,
        severity=Severity.HIGH,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            max_threshold=36.0,
            unit="months",
            allow_perpetual=False
        ),
        deterministic_regex=r"\b(in perpetuity|indefinite(ly)?|survive forever|without limitation in time)\b",
        search_queries=[
            "term and termination survive expire years duration",
            "confidentiality obligations survive in perpetuity",
            "period of confidentiality"
        ],
        guidance="Flag perpetual duration as Violation. Mark duration > 36 months as Violation."
    ),
    ComplianceRule(
        id="rule-nda-03",
        code="NDA-03",
        name="Return or Destruction of Confidential Materials",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Must permit certified destruction as an alternative to physical return, and allow routine automated archival IT backups to be retained.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            required_elements=["return or destroy", "certify destruction", "archival backup"]
        ),
        search_queries=[
            "return or certify destruction of confidential materials",
            "archival backup electronic disaster recovery",
            "return of property upon request"
        ],
        guidance="Solely physical return without destruction option cannot be fulfilled by modern IT systems."
    ),
    ComplianceRule(
        id="rule-nda-04",
        code="NDA-04",
        name="Approved Governing Law & Exclusive Jurisdiction",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Must designate an approved commercial governing jurisdiction (Delaware, New York, or England & Wales).",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.MEDIUM,
        applicable_document_types=["NDA", "Commercial Contract"],
        parameters=RuleParameters(
            approved_values=["Delaware", "New York", "England and Wales", "California"]
        ),
        search_queries=[
            "governing law and jurisdiction venue courts",
            "laws of the State of Delaware or New York",
            "applicable law dispute resolution"
        ],
        guidance="If no governing law clause exists or unapproved forum is chosen, flag for review."
    ),
    ComplianceRule(
        id="rule-nda-05",
        code="NDA-05",
        name="Prohibition of Non-Solicitation Encroachment",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Strict prohibition on employee or contractor non-solicitation clauses being embedded into standard preliminary NDAs.",
        rule_type=RuleType.PROHIBITED_TERM,
        severity=Severity.CRITICAL,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            prohibited_terms=["solicit", "hire any employee", "non-solicitation", "recruit or induce"]
        ),
        deterministic_regex=r"\b(shall not (directly or indirectly )?(solicit|hire|recruit|entice away)|non-solicitation)\b",
        search_queries=[
            "directly or indirectly solicit recruit hire personnel employees",
            "non-solicitation of employees",
            "induce any employee to leave"
        ],
        guidance="Non-solicitation restrictions belong strictly in definitive commercial agreements, not NDAs."
    ),
    ComplianceRule(
        id="rule-nda-06",
        code="NDA-06",
        name="Permitted Compelled Disclosures / Court Orders",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Must permit disclosure required by valid court order, subpoena, or governmental regulation, subject to prompt notice.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.HIGH,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            required_elements=["court order", "subpoena", "required by law", "prompt written notice"]
        ),
        search_queries=[
            "compelled disclosure subpoena court order valid legal process",
            "required by law governmental agency prompt notice"
        ],
        guidance="Absence leaves party in contempt of court or breach of contract."
    ),
    ComplianceRule(
        id="rule-nda-07",
        code="NDA-07",
        name="Standard of Care (Reasonable Care)",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Recipient duty of care must be limited to reasonable care or same degree of care as for its own confidential information.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.MEDIUM,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            required_elements=["reasonable care", "same degree of care"],
            prohibited_terms=["highest possible care", "absolute protection", "guarantee against any loss"]
        ),
        deterministic_regex=r"\b(highest (possible|degree of) care|absolute(ly)? (secure|protect)|guarantee(s)? against (any|all) loss)\b",
        search_queries=[
            "duty of care reasonable care degree of care",
            "highest possible care absolute security guarantee"
        ],
        guidance="Reject clauses mandating 'highest possible care' or absolute guarantee."
    ),
    ComplianceRule(
        id="rule-nda-08",
        code="NDA-08",
        name="Injunctive Relief & Equitable Remedies",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Must acknowledge monetary damages alone may be inadequate, entitling non-breaching party to seek injunctive relief without bond.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            required_elements=["irreparable harm", "injunctive relief", "without bond"]
        ),
        search_queries=[
            "injunctive relief equitable remedies irreparable harm without bond",
            "specific performance breach monetary damages inadequate"
        ],
        guidance="Standard enforcement protection."
    ),
    ComplianceRule(
        id="rule-nda-09",
        code="NDA-09",
        name="No Warranty / As-Is Information Disclosure",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Discloser discloses information AS IS with no implied warranties of accuracy or completeness.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            required_elements=["as is", "no warranty", "without warranty"]
        ),
        search_queries=[
            "as is without warranty of any kind express or implied",
            "no representation or warranty accuracy completeness"
        ],
        guidance="Prevents preliminary discussions from becoming representations."
    ),
    ComplianceRule(
        id="rule-nda-10",
        code="NDA-10",
        name="Prohibition of Non-Circumvent & Exclusivity",
        rule_set_id="ruleset-nda-commercial",
        version="1.0.0",
        description="Prohibits non-circumvention, deal exclusivity, or lock-up covenants in mutual NDAs.",
        rule_type=RuleType.PROHIBITED_TERM,
        severity=Severity.HIGH,
        applicable_document_types=["NDA"],
        parameters=RuleParameters(
            prohibited_terms=["non-circumvent", "non-circumvention", "exclusive negotiation", "lock-up"]
        ),
        deterministic_regex=r"\b(non-circumvent(ion)?|exclusive negotiation|exclusivity period|lock-up)\b",
        search_queries=[
            "non-circumvent non-circumvention direct transaction",
            "exclusive negotiation lock-up exclusivity period"
        ],
        guidance="NDAs must not tie companies into exclusive business dealings."
    )
]

# ----------------- STARTER RULE SET: CONTRACT HYGIENE -----------------
STARTER_HYGIENE_RULES = [
    ComplianceRule(
        id="rule-hyg-01",
        code="HYG-01",
        name="Mutual Aggregate Liability Cap",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Agreement must include a mutual liability limitation cap (e.g. fees paid in prior 12 months).",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.CRITICAL,
        applicable_document_types=["Commercial Contract", "MSA", "SOW"],
        parameters=RuleParameters(
            required_elements=["limitation of liability", "aggregate liability", "fees paid"]
        ),
        search_queries=[
            "limitation of liability aggregate liability fees paid in 12 months",
            "liability cap maximum liability"
        ],
        guidance="Uncapped liability exposes the company to existential financial risk."
    ),
    ComplianceRule(
        id="rule-hyg-02",
        code="HYG-02",
        name="Termination for Convenience Notice Period",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Termination for convenience must require a minimum of 30 days prior written notice.",
        rule_type=RuleType.NUMERIC_THRESHOLD,
        severity=Severity.HIGH,
        applicable_document_types=["Commercial Contract", "MSA"],
        parameters=RuleParameters(
            min_threshold=30.0,
            unit="days"
        ),
        search_queries=[
            "terminate for convenience written notice days prior",
            "termination without cause notice period"
        ],
        guidance="Notice periods below 30 days do not allow operational transition."
    ),
    ComplianceRule(
        id="rule-hyg-03",
        code="HYG-03",
        name="Prohibition of Silent Evergreen Auto-Renewal",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Automatic contract renewal without advance written notice or cancellation window is prohibited.",
        rule_type=RuleType.PROHIBITED_TERM,
        severity=Severity.HIGH,
        applicable_document_types=["Commercial Contract", "MSA"],
        parameters=RuleParameters(
            prohibited_terms=["automatically renew for successive one-year terms without notice", "evergreen"]
        ),
        deterministic_regex=r"\b(automatically renew(s)? (for|without)|evergreen contract)\b",
        search_queries=[
            "automatic renewal evergreen successive terms without notice",
            "renew automatically unless notified"
        ],
        guidance="Auto-renewal locks organizations into unwanted recurring costs."
    ),
    ComplianceRule(
        id="rule-hyg-04",
        code="HYG-04",
        name="Data Protection & Privacy Safeguards",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Contracts involving personal or customer data must mandate industry standard security and privacy compliance (GDPR/CCPA/SOC2).",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.HIGH,
        applicable_document_types=["Commercial Contract", "MSA", "DPA"],
        parameters=RuleParameters(
            required_elements=["data protection", "security measures", "applicable privacy laws"]
        ),
        search_queries=[
            "data protection security safeguards personal data GDPR CCPA",
            "technical and organizational measures confidentiality"
        ],
        guidance="Mandatory under global data privacy regulations."
    ),
    ComplianceRule(
        id="rule-hyg-05",
        code="HYG-05",
        name="Assignment and Change of Control Prior Consent",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Neither party may assign rights or obligations without prior written consent, except in merger or acquisition.",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.MEDIUM,
        applicable_document_types=["Commercial Contract", "MSA"],
        parameters=RuleParameters(
            required_elements=["assignment", "prior written consent"]
        ),
        search_queries=[
            "neither party may assign prior written consent",
            "assignment change of control merger acquisition"
        ],
        guidance="Prevents transfer of contract to competitor without knowledge."
    ),
    ComplianceRule(
        id="rule-hyg-06",
        code="HYG-06",
        name="Force Majeure Relief Clause",
        rule_set_id="ruleset-contract-hygiene",
        version="1.0.0",
        description="Must excuse performance delays caused by events beyond reasonable control (natural disasters, war, strikes, pandemics).",
        rule_type=RuleType.REQUIRED_CLAUSE,
        severity=Severity.LOW,
        applicable_document_types=["Commercial Contract", "MSA"],
        parameters=RuleParameters(
            required_elements=["force majeure", "beyond reasonable control", "acts of god"]
        ),
        search_queries=[
            "force majeure acts of god war epidemic strikes",
            "events beyond reasonable control excuse performance"
        ],
        guidance="Standard business continuity risk mitigation."
    )
]


class RuleEngine:
    """
    Versioned compliance rule engine.
    Ensures rules are immutable data, changes produce new semantic versions,
    and reports remain reproducible.
    """
    def __init__(self):
        # Key: (ruleset_id, version) -> RuleSet
        self._ruleset_versions: dict[str, RuleSet] = {}
        # Key: ruleset_id -> latest_version string
        self._latest_versions: dict[str, str] = {}
        self._seed_starter_libraries()

    def _seed_starter_libraries(self):
        # 1. Commercial NDA v1.0.0
        nda_set = RuleSet(
            id="ruleset-nda-commercial",
            name="Standard Commercial NDA Ruleset",
            version="1.0.0",
            description="Comprehensive compliance rules for commercial non-disclosure and confidentiality agreements.",
            document_type="NDA",
            rules=STARTER_NDA_RULES,
            is_default=True
        )
        self.register_rule_set(nda_set)

        # 2. Contract Hygiene v1.0.0
        hygiene_set = RuleSet(
            id="ruleset-contract-hygiene",
            name="General Contract Hygiene Ruleset",
            version="1.0.0",
            description="Foundational contract risk, liability caps, notice, and operational hygiene controls.",
            document_type="Commercial Contract",
            rules=STARTER_HYGIENE_RULES,
            is_default=False
        )
        self.register_rule_set(hygiene_set)

    def register_rule_set(self, ruleset: RuleSet):
        key = f"{ruleset.id}:{ruleset.version}"
        self._ruleset_versions[key] = ruleset
        self._latest_versions[ruleset.id] = ruleset.version

    def get_rule_set(self, ruleset_id: str, version: str | None = None) -> RuleSet:
        target_version = version or self._latest_versions.get(ruleset_id)
        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule set '{ruleset_id}' not found."
            )
        key = f"{ruleset_id}:{target_version}"
        ruleset = self._ruleset_versions.get(key)
        if not ruleset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule set '{ruleset_id}' version '{target_version}' not found."
            )
        return ruleset

    def list_rule_sets(self) -> list[RuleSet]:
        """Returns the latest version of all registered rule sets."""
        result = []
        for r_id, ver in self._latest_versions.items():
            result.append(self._ruleset_versions[f"{r_id}:{ver}"])
        return result

    def list_versions_for_set(self, ruleset_id: str) -> list[str]:
        versions = []
        for key in self._ruleset_versions.keys():
            if key.startswith(f"{ruleset_id}:"):
                versions.append(key.split(":", 1)[1])
        return sorted(versions)

    def create_new_version(
        self,
        ruleset_id: str,
        new_version: str,
        updated_rules: list[ComplianceRule],
        description: str | None = None
    ) -> RuleSet:
        """
        Creates a new version of a rule set without overwriting previous versions.
        Ensures auditability and past check reproducibility.
        """
        current = self.get_rule_set(ruleset_id)
        key = f"{ruleset_id}:{new_version}"
        if key in self._ruleset_versions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Version '{new_version}' already exists for rule set '{ruleset_id}'."
            )

        new_set = RuleSet(
            id=ruleset_id,
            name=current.name,
            version=new_version,
            description=description or current.description,
            document_type=current.document_type,
            rules=updated_rules,
            is_default=current.is_default
        )
        self.register_rule_set(new_set)
        return new_set


rule_engine = RuleEngine()
