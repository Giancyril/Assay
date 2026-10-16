from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LedgerEventType(StrEnum):
    DOCUMENT_INGESTED = "DOCUMENT_INGESTED"
    AUDIT_INITIATED = "AUDIT_INITIATED"
    FINDING_RECORDED = "FINDING_RECORDED"
    ACTION_RESOLVED = "ACTION_RESOLVED"
    WAIVER_GRANTED = "WAIVER_GRANTED"
    CERTIFICATE_ISSUED = "CERTIFICATE_ISSUED"
    POLICY_MODIFIED = "POLICY_MODIFIED"


class LedgerBlock(BaseModel):
    block_index: int = Field(..., ge=0, description="Monotonically increasing block index")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: LedgerEventType
    document_id: str
    actor: str = Field(default="system:compliance_orchestrator")
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str = Field(..., description="SHA-256 hash of canonical event payload")
    prev_hash: str = Field(..., description="SHA-256 hash of the previous ledger block")
    block_hash: str = Field(..., description="SHA-256 hash sealing this block")


class LedgerVerificationResult(BaseModel):
    is_valid: bool = Field(..., description="True if cryptographic chain is completely intact")
    total_blocks: int = Field(..., ge=0)
    last_block_hash: str
    tampered_block_index: int | None = Field(default=None)
    verification_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str


class LedgerAppendRequest(BaseModel):
    document_id: str
    event_type: LedgerEventType
    actor: str = Field(default="system:compliance_orchestrator")
    payload: dict[str, Any] = Field(default_factory=dict)
