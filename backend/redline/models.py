from enum import StrEnum

from pydantic import BaseModel, Field


class DiffOp(StrEnum):
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
    tokens: list[DiffToken] = Field(default_factory=list)
    legal_rationale: str
    page_number: int | None = None
    char_start: int | None = None
    char_end: int | None = None
