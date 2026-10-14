from typing import Any

from pydantic import BaseModel, Field


class ClauseChunk(BaseModel):
    id: str
    document_id: str
    section_number: str | None = None  # e.g., "1", "12.3", "Article IV"
    section_title: str  # e.g., "Non-Disclosure Obligations"
    content: str  # Full clause text
    page_start: int  # 1-indexed page
    page_end: int
    char_start_doc: int  # Offset within complete document
    char_end_doc: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    chunk: ClauseChunk
    vector_score: float = 0.0
    fts_score: float = 0.0
    combined_score: float = 0.0
    match_type: str = "hybrid"  # vector, fts, or hybrid
