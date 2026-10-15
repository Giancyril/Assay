import uuid
from datetime import UTC, datetime
from typing import Optional

from backend.agent.findings import Finding
from backend.benchmark.models import (
    ComplianceStatusTier,
    CrosswalkItem,
    RegulatoryBenchmarkReport,
    RegulatoryStandard,
    StandardComplianceStatus,
    StandardRequirement,
)
from backend.ingestion.models import ParsedDocument


STANDARD_CATALOG: dict[RegulatoryStandard, list[StandardRequirement]] = {
    RegulatoryStandard.GDPR: [
        StandardRequirement(
            requirement_id="GDPR-Art28",
            standard=RegulatoryStandard.GDPR,
            title="Data Processing Agreement & Subprocessor Authorization",
            clause_summary="Mandatory DPA specifying subject matter, duration, nature, and prior subprocessor consent.",
            weight=1.5,
        ),
        StandardRequirement(
            requirement_id="GDPR-Art32",
            standard=RegulatoryStandard.GDPR,
            title="Security of Processing & Encryption",
            clause_summary="Technical and organizational measures including encryption at rest and in transit.",
            weight=1.0,
        ),
        StandardRequirement(
            requirement_id="GDPR-Art33",
            standard=RegulatoryStandard.GDPR,
            title="72-Hour Personal Data Breach Notification",
            clause_summary="Immediate notification to supervisory authority and data controller without undue delay within 72 hours.",
            weight=2.0,
        ),
        StandardRequirement(
            requirement_id="GDPR-Art44",
            standard=RegulatoryStandard.GDPR,
            title="Cross-Border Data Transfer Safeguards",
            clause_summary="Standard Contractual Clauses (SCCs) or adequacy decisions for international data transfers.",
            weight=1.5,
        ),
    ],
    RegulatoryStandard.HIPAA: [
        StandardRequirement(
            requirement_id="HIPAA-164.308",
            standard=RegulatoryStandard.HIPAA,
            title="Business Associate Agreement (BAA) Safeguards",
            clause_summary="Administrative safeguards and mandatory BAA execution prior to PHI disclosure.",
            weight=2.0,
        ),
        StandardRequirement(
            requirement_id="HIPAA-164.312",
            standard=RegulatoryStandard.HIPAA,
            title="Technical Safeguards & PHI Encryption",
            clause_summary="Access controls, audit logging, and encryption mechanisms for protected health information.",
            weight=1.5,
        ),
        StandardRequirement(
            requirement_id="HIPAA-164.404",
            standard=RegulatoryStandard.HIPAA,
            title="PHI Breach Notification Protocol",
            clause_summary="Written breach notification without unreasonable delay and in no case later than 60 calendar days.",
            weight=1.5,
        ),
    ],
    RegulatoryStandard.SOC2_TYPE2: [
        StandardRequirement(
            requirement_id="SOC2-CC6.1",
            standard=RegulatoryStandard.SOC2_TYPE2,
            title="Logical & Physical Access Controls",
            clause_summary="Role-based access controls, MFA, and perimeter defense controls.",
            weight=1.0,
        ),
        StandardRequirement(
            requirement_id="SOC2-CC7.2",
            standard=RegulatoryStandard.SOC2_TYPE2,
            title="Incident Detection & Remediation SLA",
            clause_summary="Security incident identification, escalation, and documented remediation timelines.",
            weight=1.5,
        ),
        StandardRequirement(
            requirement_id="SOC2-CC9.2",
            standard=RegulatoryStandard.SOC2_TYPE2,
            title="Vendor Risk Management & Audit Rights",
            clause_summary="Right to inspect vendor security controls and obtain third-party audit reports annually.",
            weight=1.5,
        ),
    ],
    RegulatoryStandard.ISO27001: [
        StandardRequirement(
            requirement_id="ISO-A.13.2",
            standard=RegulatoryStandard.ISO27001,
            title="Information Transfer & Confidentiality Agreements",
            clause_summary="Formal agreements defining information transfer security and binding confidentiality obligations.",
            weight=1.0,
        ),
        StandardRequirement(
            requirement_id="ISO-A.15.1",
            standard=RegulatoryStandard.ISO27001,
            title="Information Security in Supplier Relationships",
            clause_summary="Documented security requirements and monitoring processes for all third-party suppliers.",
            weight=1.5,
        ),
        StandardRequirement(
            requirement_id="ISO-A.16.1",
            standard=RegulatoryStandard.ISO27001,
            title="Information Security Incident Management",
            clause_summary="Consistent and effective management of information security events and weaknesses.",
            weight=1.5,
        ),
    ],
}


class RegulatoryCrosswalkEngine:
    """Evaluates contracts and compliance findings against multi-standard regulatory frameworks."""

    @classmethod
    def evaluate(
        cls,
        document: ParsedDocument,
        findings: list[Finding],
    ) -> RegulatoryBenchmarkReport:
        doc_text = (document.full_text if hasattr(document, "full_text") and document.full_text else "").lower()

        # Extract non-compliant findings
        failed_findings: list[Finding] = []
        for f in findings:
            v = ""
            if hasattr(f, "verdict") and f.verdict:
                v = getattr(f.verdict, "value", str(f.verdict)).lower()
            elif hasattr(f, "status") and f.status:
                v = getattr(f.status, "value", str(f.status)).lower()
            if v in ["violation", "needs_review", "failed", "fail", "warning"]:
                failed_findings.append(f)

        crosswalk_matrix: list[CrosswalkItem] = []
        gaps_by_standard: dict[RegulatoryStandard, list[str]] = {s: [] for s in STANDARD_CATALOG}

        # Cross-reference failed findings with standards
        for f in failed_findings:
            title = getattr(f, "rule_name", getattr(f, "rule_title", f.rule_id)).lower()
            reasoning = getattr(f, "reasoning", getattr(f, "explanation", "")).lower()
            combined = f"{title} {reasoning}"

            affected: list[RegulatoryStandard] = []
            citations: dict[str, str] = {}

            if "breach" in combined or "incident" in combined or "72" in combined:
                affected.extend([
                    RegulatoryStandard.GDPR,
                    RegulatoryStandard.HIPAA,
                    RegulatoryStandard.SOC2_TYPE2,
                    RegulatoryStandard.ISO27001,
                ])
                citations["GDPR"] = "Art. 33(1) (72h Notification)"
                citations["HIPAA"] = "45 CFR § 164.404 (Breach Notification)"
                citations["SOC2_TYPE2"] = "CC7.2 (Incident Management)"
                citations["ISO27001"] = "A.16.1 (Incident Response)"
                for s in affected:
                    gaps_by_standard[s].append("Timely Security Incident & Breach Notification SLA")

            if "audit" in combined or "inspection" in combined:
                affected.extend([RegulatoryStandard.SOC2_TYPE2, RegulatoryStandard.ISO27001])
                citations["SOC2_TYPE2"] = "CC9.2 (Customer Audit Rights)"
                citations["ISO27001"] = "A.15.1 (Supplier Security Monitoring)"
                gaps_by_standard[RegulatoryStandard.SOC2_TYPE2].append("Independent Third-Party Audit & Inspection Rights")
                gaps_by_standard[RegulatoryStandard.ISO27001].append("Supplier Relationship Security Verification")

            if "confidential" in combined or "perpetual" in combined:
                affected.append(RegulatoryStandard.ISO27001)
                citations["ISO27001"] = "A.13.2.4 (Confidentiality & Non-Disclosure Agreements)"
                gaps_by_standard[RegulatoryStandard.ISO27001].append("Term-bounded Confidentiality Agreement")

            if "subprocessor" in combined or "personal data" in combined or "dpa" in combined:
                affected.extend([RegulatoryStandard.GDPR, RegulatoryStandard.HIPAA])
                citations["GDPR"] = "Art. 28(2) (Subprocessor Consent)"
                citations["HIPAA"] = "45 CFR § 164.502(e) (Business Associate Subcontractors)"
                gaps_by_standard[RegulatoryStandard.GDPR].append("Data Processing Agreement & Subprocessor Controls")
                gaps_by_standard[RegulatoryStandard.HIPAA].append("Business Associate Subcontractor Safeguards")

            if "liability" in combined or "indemnif" in combined:
                affected.append(RegulatoryStandard.SOC2_TYPE2)
                citations["SOC2_TYPE2"] = "CC9.2 (Risk Mitigation & Commercial Exposure)"
                gaps_by_standard[RegulatoryStandard.SOC2_TYPE2].append("Contractual Liability and Exposure Boundaries")

            if affected:
                crosswalk_matrix.append(
                    CrosswalkItem(
                        finding_id=getattr(f, "id", getattr(f, "finding_id", "f-unknown")),
                        rule_id=f.rule_id,
                        rule_name=getattr(f, "rule_name", getattr(f, "rule_title", f.rule_id)),
                        affected_standards=list(set(affected)),
                        citations=citations,
                        impact_level=getattr(getattr(f, "severity", None), "value", str(getattr(f, "severity", "HIGH"))).upper(),
                    )
                )

        # Calculate scores per standard
        breakdowns: dict[str, StandardComplianceStatus] = {}
        total_scores = []

        for standard, reqs in STANDARD_CATALOG.items():
            total_reqs = len(reqs)
            gaps = list(set(gaps_by_standard[standard]))
            failed_count = min(len(gaps), total_reqs)
            passed_count = total_reqs - failed_count

            # Score = (passed / total) * 100
            score = round((passed_count / total_reqs) * 100.0, 1)
            total_scores.append(score)

            if score >= 90.0:
                tier = ComplianceStatusTier.COMPLIANT
            elif score >= 60.0:
                tier = ComplianceStatusTier.PARTIAL
            else:
                tier = ComplianceStatusTier.NON_COMPLIANT

            breakdowns[standard.value] = StandardComplianceStatus(
                standard=standard,
                score=score,
                tier=tier,
                passed_requirements_count=passed_count,
                failed_requirements_count=failed_count,
                total_requirements_count=total_reqs,
                key_gaps=gaps,
            )

        composite_index = round(sum(total_scores) / len(total_scores), 1) if total_scores else 100.0

        summary = (
            f"Multi-Standard Benchmark completed with Global Compliance Index of {composite_index}/100. "
            f"Evaluated {len(STANDARD_CATALOG)} regulatory frameworks across {len(crosswalk_matrix)} crosswalked compliance findings."
        )

        return RegulatoryBenchmarkReport(
            report_id=f"bench-{uuid.uuid4().hex[:8]}",
            document_id=document.id,
            created_at=datetime.now(UTC),
            global_compliance_index=composite_index,
            standard_breakdowns=breakdowns,
            crosswalk_matrix=crosswalk_matrix,
            executive_summary=summary,
        )


benchmark_engine = RegulatoryCrosswalkEngine()
