from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.rules.models import ComplianceRule, Verdict, PrecheckResult
from backend.indexing.models import ClauseChunk


class ComplianceCheckState(BaseModel):
    document_id: str
    rule_id: str
    rule: ComplianceRule
    full_document_text: str = ""
    retrieved_chunks: List[ClauseChunk] = Field(default_factory=list)
    searches_run: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    precheck_result: Optional[PrecheckResult] = None
    
    # Verdict & Evidence
    verdict: Optional[Verdict] = None
    verbatim_quote: Optional[str] = None
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    evidence_verified: bool = False
    rejection_reason: Optional[str] = None
    
    # Analysis & Recommendation
    reasoning: str = ""
    recommended_action: str = ""
    confidence: float = 0.0
    requires_human_review: bool = False
    
    # Finding metadata
    finding_id: Optional[str] = None
    error: Optional[str] = None
