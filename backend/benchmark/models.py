from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RegulatoryStandard(str, Enum):
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    SOC2_TYPE2 = "SOC2_TYPE2"
    ISO27001 = "ISO27001"
    CCPA_CPRA = "CCPA_CPRA"
    PCI_DSS = "PCI_DSS"


class ComplianceStatusTier(str, Enum):
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"


class StandardRequirement(BaseModel):
    requirement_id: str = Field(..., description="Unique regulatory clause code (e.g., GDPR-Art33)")
    standard: RegulatoryStandard = Field(..., description="Target statutory or industry standard")
    title: str = Field(..., description="Requirement title")
    clause_summary: str = Field(..., description="Description of legal obligation")
    mandatory: bool = Field(default=True)
    weight: float = Field(default=1.0)


class StandardComplianceStatus(BaseModel):
    standard: RegulatoryStandard
    score: float = Field(..., ge=0.0, le=100.0, description="Percentage compliance score (0-100)")
    tier: ComplianceStatusTier
    passed_requirements_count: int = Field(default=0)
    failed_requirements_count: int = Field(default=0)
    total_requirements_count: int = Field(default=0)
    key_gaps: list[str] = Field(default_factory=list)


class CrosswalkItem(BaseModel):
    finding_id: str
    rule_id: str
    rule_name: str
    affected_standards: list[RegulatoryStandard]
    citations: dict[str, str] = Field(default_factory=dict, description="Standard to section citations")
    impact_level: str = Field(default="HIGH")


class RegulatoryBenchmarkReport(BaseModel):
    report_id: str
    document_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    global_compliance_index: float = Field(..., ge=0.0, le=100.0, description="Weighted composite compliance index")
    standard_breakdowns: dict[str, StandardComplianceStatus] = Field(default_factory=dict)
    crosswalk_matrix: list[CrosswalkItem] = Field(default_factory=list)
    executive_summary: str
