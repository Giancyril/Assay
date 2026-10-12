from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DocumentFileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


class TextSpan(BaseModel):
    page_number: int  # 1-indexed
    char_start_page: int
    char_end_page: int
    char_start_doc: int
    char_end_doc: int
    text: str
    block_type: str = "paragraph"  # paragraph, heading, table_cell, list_item


class DocumentPage(BaseModel):
    page_number: int  # 1-indexed
    text: str
    char_start_doc: int
    char_end_doc: int
    is_ocr: bool = False
    spans: List[TextSpan] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    id: str
    filename: str
    file_type: DocumentFileType
    file_size_bytes: int
    storage_path: str
    full_text: str
    page_count: int
    is_ocr: bool = False
    pages: List[DocumentPage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
