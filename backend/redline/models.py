from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DiffOp(str, Enum):
    EQUAL = "equal"
    DELETE = "delete"
    INSERT = "insert"


class DiffToken(BaseModel):
    op: DiffOp
    text: str


class RedlineDiff(BaseModel):
    finding_id: str
    rule_code: str
    rule_name: str
    original_text: str
    remediated_text: str
    inline_markup: str
    unified_diff: str
    tokens: List[DiffToken] = Field(default_factory=list)
    legal_rationale: str
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None