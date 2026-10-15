import re
import uuid

from backend.agent.findings import Finding
from backend.ingestion.models import ParsedDocument
from backend.risk.models import (
    ExposureCategory,
    FinancialExposureReport,
    FinancialRiskExposureItem,
    RiskTier,
)


class FinancialExposureCalculator:
    """Calculates monetary liability exposure and quantitative risk scores for contract findings."""

    @classmethod
    def evaluate(
        cls,
        document: ParsedDocument,
        findings: list[Finding] | None = None,
    ) -> FinancialExposureReport:
        findings = findings or []
        items: list[FinancialRiskExposureItem] = []
        text = document.full_text
        lower_text = text.lower()

        # Check for perpetual obligation (finding or text match)
        has_perpetual_finding = any(f.rule_id == "rule-nda-02" and f.verdict.value == "VIOLATION" for f in findings)
        has_perpetual_text = bool(re.search(r"(?i)(perpetual|indefinite|survive indefinitely)", lower_text))
        if has_perpetual_finding or has_perpetual_text:
            min_exp = 25000.0
            max_exp = 150000.0
            prob = 0.35
            items.append(
                FinancialRiskExposureItem(
                    category=ExposureCategory.OPERATIONAL_BREACH,
                    title="Perpetual Confidentiality Tail Liability",
                    risk_tier=RiskTier.HIGH,
                    rule_id="rule-nda-02",
                    estimated_min_exposure_usd=min_exp,
                    estimated_max_exposure_usd=max_exp,
                    probability=prob,
                    expected_loss_usd=round(((min_exp + max_exp) / 2.0) * prob, 2),
                    legal_basis="Indefinite confidentiality obligations generate indefinite monitoring, retention, and breach liabilities.",
                    mitigation_strategy="Cap confidentiality survival at 3 to 5 years from disclosure date.",
                )
            )

        # Check for non-solicitation restrictions
        has_nonsolicit_finding = any(f.rule_id == "rule-nda-05" and f.verdict.value == "VIOLATION" for f in findings)
        has_nonsolicit_text = bool(re.search(r"(?i)(non-solicit|solicit.*employees?|hire.*employees?)", lower_text))
        if has_nonsolicit_finding or has_nonsolicit_text:
            min_exp = 50000.0
            max_exp = 250000.0
            prob = 0.25
            items.append(
                FinancialRiskExposureItem(
                    category=ExposureCategory.REGULATORY_PENALTY,
                    title="Restrictive Employee Covenant Exposure",
                    risk_tier=RiskTier.MEDIUM,
                    rule_id="rule-nda-05",
                    estimated_min_exposure_usd=min_exp,
                    estimated_max_exposure_usd=max_exp,
                    probability=prob,
                    expected_loss_usd=round(((min_exp + max_exp) / 2.0) * prob, 2),
                    legal_basis="Non-solicitation covenants trigger talent acquisition friction and potential enforcement injunction damages.",
                    mitigation_strategy="Carve out general non-targeted public recruiting advertisements.",
                )
            )

        # Check for uncapped liability
        has_cap = bool(
            re.search(
                r"(?i)(?:aggregate liability|limitation of liability|liability.*cap|shall not exceed)",
                lower_text,
            )
        )
        if not has_cap:
            min_exp = 200000.0
            max_exp = 1500000.0
            prob = 0.15
            items.append(
                FinancialRiskExposureItem(
                    category=ExposureCategory.UNLIMITED_LIABILITY,
                    title="Uncapped / Unlimited Consequential Liability",
                    risk_tier=RiskTier.CRITICAL,
                    rule_id="clause-liability-uncapped",
                    estimated_min_exposure_usd=min_exp,
                    estimated_max_exposure_usd=max_exp,
                    probability=prob,
                    expected_loss_usd=round(((min_exp + max_exp) / 2.0) * prob, 2),
                    legal_basis="Absence of an express liability ceiling exposes all company assets to consequential and punitive damages.",
                    mitigation_strategy="Insert mutual aggregate liability limitation capped at total fees paid in prior 12 months.",
                )
            )

        # Check for broad indemnity obligations
        has_indemnity = bool(re.search(r"(?i)(?:indemnif|hold harmless|defend and hold)", lower_text))
        if has_indemnity:
            min_exp = 100000.0
            max_exp = 750000.0
            prob = 0.20
            items.append(
                FinancialRiskExposureItem(
                    category=ExposureCategory.INDEMNIFICATION,
                    title="Broad Third-Party Indemnification Exposure",
                    risk_tier=RiskTier.HIGH,
                    rule_id="clause-indemnity-broad",
                    estimated_min_exposure_usd=min_exp,
                    estimated_max_exposure_usd=max_exp,
                    probability=prob,
                    expected_loss_usd=round(((min_exp + max_exp) / 2.0) * prob, 2),
                    legal_basis="Unqualified indemnity shifts third-party defense costs and settlement liabilities onto your balance sheet.",
                    mitigation_strategy="Restrict indemnity strictly to direct IP infringement with prompt notice and sole defense control.",
                )
            )

        # Calculate Totals
        total_min = sum(i.estimated_min_exposure_usd for i in items)
        total_max = sum(i.estimated_max_exposure_usd for i in items)
        total_expected_loss = sum(i.expected_loss_usd for i in items)

        # Compute Score (0 to 100)
        # Baseline score calculation: $500,000 expected loss maps to ~100
        score = min(100.0, (total_expected_loss / 3500.0))
        score = round(score, 1)

        if score <= 15.0:
            tier = RiskTier.LOW
            grade = "A (Low Risk)"
        elif score <= 40.0:
            tier = RiskTier.MEDIUM
            grade = "B (Moderate Risk)"
        elif score <= 70.0:
            tier = RiskTier.HIGH
            grade = "C (Elevated Risk)"
        else:
            tier = RiskTier.CRITICAL
            grade = "D (High Risk)" if score <= 85.0 else "F (Critical Risk)"

        key_vulns = [i.title for i in items if i.risk_tier in (RiskTier.CRITICAL, RiskTier.HIGH)]
        if not key_vulns and items:
            key_vulns = [items[0].title]

        summary = (
            f"Evaluated {len(items)} financial exposure categories. Total maximum potential exposure "
            f"is estimated at ${total_max:,.2f} USD with an expected risk-weighted loss of "
            f"${total_expected_loss:,.2f} USD ({grade})."
        )

        return FinancialExposureReport(
            report_id=f"risk-{uuid.uuid4().hex[:8]}",
            document_id=document.id,
            document_filename=document.filename,
            overall_risk_tier=tier,
            overall_risk_score=score,
            exposure_grade=grade,
            total_min_exposure_usd=round(total_min, 2),
            total_max_exposure_usd=round(total_max, 2),
            total_expected_loss_usd=round(total_expected_loss, 2),
            exposure_breakdown=items,
            key_vulnerabilities=key_vulns,
            executive_summary=summary,
        )
