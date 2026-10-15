from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExposureCategory(StrEnum):
    UNLIMITED_LIABILITY = "unlimited_liability"
    INDEMNIFICATION = "indemnification"
    REGULATORY_PENALTY = "regulatory_penalty"
    IP_INFRINGEMENT = "ip_infringement"
    OPERATIONAL_BREACH = "operational_breach"


class FinancialRiskExposureItem(BaseModel):
    category: ExposureCategory
    title: str
    risk_tier: RiskTier
    rule_id: str | None = None
    estimated_min_exposure_usd: float = Field(..., ge=0.0)
    estimated_max_exposure_usd: float = Field(..., ge=0.0)
    probability: float = Field(..., ge=0.0, le=1.0, description="Estimated breach/dispute probability (0.0 to 1.0)")
    expected_loss_usd: float = Field(..., ge=0.0, description="Probability-weighted expected loss")
    legal_basis: str
    mitigation_strategy: str


class FinancialExposureReport(BaseModel):
    report_id: str
    document_id: str
    document_filename: str
    overall_risk_tier: RiskTier
    overall_risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="Composite risk index: 0 = negligible, 100 = catastrophic"
    )
    exposure_grade: str = Field(..., description="Grade A (Lowest Risk) to F (Highest Risk)")
    total_min_exposure_usd: float
    total_max_exposure_usd: float
    total_expected_loss_usd: float
    exposure_breakdown: list[FinancialRiskExposureItem] = Field(default_factory=list)
    key_vulnerabilities: list[str] = Field(default_factory=list)
    executive_summary: str
    evaluated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
