"""
Pydantic models for visual document highlighting and jump-to-source navigation.

Each HighlightAnnotation maps a compliance finding to precise character offsets and
page numbers within the original document, enabling the frontend to visually mark
problematic clauses and jump directly to the relevant page/position.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class HighlightColor(str):
    """Semantic color tokens for finding severity."""
    VIOLATION = "#FF4D4D"       # red
    NEEDS_REVIEW = "#FFB347"    # amber
    COMPLIANT = "#4CAF50"       # green
    NOT_APPLICABLE = "#9E9E9E"  # grey


VERDICT_COLOR_MAP: dict[str, str] = {
    "violation": HighlightColor.VIOLATION,
    "needs_review": HighlightColor.NEEDS_REVIEW,
    "compliant": HighlightColor.COMPLIANT,
    "not_applicable": HighlightColor.NOT_APPLICABLE,
}


class HighlightAnnotation(BaseModel):
    """
    A single highlight annotation that maps a finding to a text span
    within the original document for visual rendering in the frontend.
    """
    finding_id: str
    document_id: str
    rule_code: str
    rule_name: str
    verdict: str
    severity: str

    # Positioning
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    # Visual metadata
    color: str = Field(default="#FF4D4D", description="Hex color for the highlight overlay")
    label: str = Field(default="", description="Short display label shown in the annotation callout")
    verbatim_quote: Optional[str] = None

    # Navigation hint for PDF viewer
    jump_url: Optional[str] = Field(
        default=None,
        description="Deep-link URL to scroll the PDF viewer to the correct page and offset"
    )

    # Tooltip content for hover-over
    tooltip_summary: str = ""


class DocumentHighlightMap(BaseModel):
    """
    Complete highlight map for an entire document, containing all
    HighlightAnnotations grouped for efficient frontend consumption.
    """
    document_id: str
    filename: str
    total_annotations: int
    annotations: list[HighlightAnnotation] = Field(default_factory=list)
    # Index: page_number -> list of annotation IDs on that page
    page_index: dict[str, list[str]] = Field(default_factory=dict)
