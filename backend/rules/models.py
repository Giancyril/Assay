from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    REQUIRED_CLAUSE = "required_clause"
    PROHIBITED_TERM = "prohibited_term"
    NUMERIC_THRESHOLD = "numeric_threshold"
    CONDITIONAL = "conditional"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(str, Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class RuleParameters(BaseModel):
    required_elements: Optional[List[str]] = None
    prohibited_terms: Optional[List[str]] = None
    max_threshold: Optional[float] = None
    min_threshold: Optional[float] = None
    unit: Optional[str] = None  # "months", "days", "usd", "percent"
    allow_perpetual: Optional[bool] = None
    approved_values: Optional[List[str]] = None
    condition: Optional[str] = None
    then_requirement: Optional[str] = None
    custom: Dict[str, Any] = Field(default_factory=dict)


class ComplianceRule(BaseModel):
    id: str
    code: str
    name: str
    rule_set_id: str
    version: str = "1.0.0"
    description: str
    rule_type: RuleType
    severity: Severity
    applicable_document_types: List[str] = Field(default_factory=lambda: ["NDA", "Commercial Contract"])
    parameters: RuleParameters = Field(default_factory=RuleParameters)
    deterministic_regex: Optional[str] = None
    search_queries: List[str] = Field(default_factory=list)
    guidance: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuleSet(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str
    document_type: str = "NDA"
    rules: List[ComplianceRule] = Field(default_factory=list)
    is_default: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PrecheckResult(BaseModel):
    has_deterministic_verdict: bool = False
    verdict: Optional[Verdict] = None
    evidence_quote: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: float = 0.0
    matched_term: Optional[str] = None
