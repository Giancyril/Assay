from pydantic import BaseModel, Field

from backend.indexing.models import ClauseChunk
from backend.rules.models import ComplianceRule, PrecheckResult, Verdict


class ComplianceCheckState(BaseModel):
    document_id: str
    rule_id: str
    rule: ComplianceRule
    full_document_text: str = ""
    retrieved_chunks: list[ClauseChunk] = Field(default_factory=list)
    searches_run: list[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    precheck_result: PrecheckResult | None = None

    # Verdict & Evidence
    verdict: Verdict | None = None
    verbatim_quote: str | None = None
    page_number: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    evidence_verified: bool = False
    rejection_reason: str | None = None

    # Analysis & Recommendation
    reasoning: str = ""
    recommended_action: str = ""
    confidence: float = 0.0
    requires_human_review: bool = False

    # Finding metadata
    finding_id: str | None = None
    error: str | None = None
