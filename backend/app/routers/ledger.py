import logging

from fastapi import APIRouter, HTTPException, Query, status

from backend.ledger.models import (
    LedgerAppendRequest,
    LedgerBlock,
    LedgerVerificationResult,
)
from backend.ledger.service import audit_ledger_service

logger = logging.getLogger("compliance_agent.ledger")

router = APIRouter(prefix="/api/ledger", tags=["Cryptographic Audit Ledger & Timeline"])


@router.get(
    "/timeline",
    response_model=list[LedgerBlock],
    status_code=status.HTTP_200_OK,
)
async def get_ledger_timeline(document_id: str | None = Query(default=None, description="Optional document filter")):
    """Returns the chronological audit event ledger blocks, optionally filtered by document."""
    return audit_ledger_service.get_timeline(document_id=document_id)


@router.get(
    "/block/{block_index}",
    response_model=LedgerBlock,
    status_code=status.HTTP_200_OK,
)
async def get_ledger_block(block_index: int):
    """Retrieves an individual cryptographic block by its index."""
    block = audit_ledger_service.get_block(block_index)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ledger block {block_index} does not exist.",
        )
    return block


@router.post(
    "/record",
    response_model=LedgerBlock,
    status_code=status.HTTP_201_CREATED,
)
async def record_audit_event(request: LedgerAppendRequest):
    """Appends an immutable, cryptographically sealed compliance event to the ledger."""
    logger.info("Appending ledger block for doc '%s': %s", request.document_id, request.event_type)
    block = audit_ledger_service.append_event(
        document_id=request.document_id,
        event_type=request.event_type,
        actor=request.actor,
        payload=request.payload,
    )
    return block


@router.get(
    "/verify",
    response_model=LedgerVerificationResult,
    status_code=status.HTTP_200_OK,
)
async def verify_ledger_integrity():
    """Cryptographically validates the hash chain from genesis to head block, ensuring zero tampering."""
    return audit_ledger_service.verify_integrity()
