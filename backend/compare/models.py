from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ConflictType(StrEnum):
    GOVERNING_LAW_MISMATCH = "governing_law_mismatch"
    DURATION_MISMATCH = "duration_mismatch"
    NOTICE_PERIOD_MISMATCH = "notice_period_mismatch"
    CONFIDENTIALITY_SCOPE_MISMATCH = "confidentiality_scope_mismatch"
    LIABILITY_CAP_MISMATCH = "liability_cap_mismatch"
    CUSTOM_CONFLICT = "custom_conflict"


class ConflictSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClauseComparisonItem(BaseModel):
    category: str
    doc_a_clause: str | None = None
    doc_b_clause: str | None = None
    doc_a_extracted_value: str | None = None
    doc_b_extracted_value: str | None = None
    has_conflict: bool = False
    conflict_type: ConflictType | None = None
    severity: ConflictSeverity | None = None
    explanation: str | None = None
    recommended_resolution: str | None = None


class DocumentConflict(BaseModel):
    id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    topic: str
    doc_a_excerpt: str
    doc_b_excerpt: str
    explanation: str
    remediation_suggestion: str


class ComparativeAuditRequest(BaseModel):
    doc_a_id: str = Field(..., description="Primary document ID")
    doc_b_id: str = Field(..., description="Secondary document ID")
    doc_a_role: str = Field(default="Primary Agreement", description="Label for Document A")
    doc_b_role: str = Field(default="Secondary / Addendum", description="Label for Document B")


class ComparativeAuditResult(BaseModel):
    comparison_id: str
    doc_a_id: str
    doc_b_id: str
    doc_a_filename: str
    doc_b_filename: str
    total_conflicts: int
    critical_conflicts: int
    high_conflicts: int
    alignment_score: float = Field(..., ge=0.0, le=100.0, description="100% means perfectly aligned")
    conflicts: list[DocumentConflict] = Field(default_factory=list)
    clause_comparisons: list[ClauseComparisonItem] = Field(default_factory=list)
    compared_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
