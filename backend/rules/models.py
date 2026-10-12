from datetime import UTC, datetime
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


class RuleParameters(BaseModel):
    required_elements: list[str] | None = None
    prohibited_terms: list[str] | None = None
    max_threshold: float | None = None
    min_threshold: float | None = None
    unit: str | None = None  # "months", "days", "usd", "percent"
    allow_perpetual: bool | None = None
    approved_values: list[str] | None = None
    condition: str | None = None
    then_requirement: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


class ComplianceRule(BaseModel):
    id: str
    code: str
    name: str
    rule_set_id: str
    version: str = "1.0.0"
    description: str
    rule_type: RuleType
    severity: Severity
    applicable_document_types: list[str] = Field(default_factory=lambda: ["NDA", "Commercial Contract"])
    parameters: RuleParameters = Field(default_factory=RuleParameters)
    deterministic_regex: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    guidance: str | None = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RuleSet(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str
    document_type: str = "NDA"
    rules: list[ComplianceRule] = Field(default_factory=list)
    is_default: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PrecheckResult(BaseModel):
    has_deterministic_verdict: bool = False
    verdict: Verdict | None = None
    evidence_quote: str | None = None
    reasoning: str | None = None
    confidence: float = 0.0
    matched_term: str | None = None
