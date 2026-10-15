import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from backend.agent.findings import findings_repository
from backend.ingestion.repository import doc_repository
from backend.remediation.engine import remediation_engine
from backend.remediation.models import (
    RemediationActionItem,
    RemediationGenerateRequest,
    RemediationPlaybook,
    RemediationStatusUpdateRequest,
)

logger = logging.getLogger("compliance_agent.remediation")

router = APIRouter(prefix="/api/remediation", tags=["Remediation & Playbooks"])


@router.post(
    "/generate",
    response_model=RemediationPlaybook,
    status_code=status.HTTP_201_CREATED,
)
async def generate_remediation_playbook(request: RemediationGenerateRequest):
    """Generates an action-oriented remediation playbook for an audited document."""
    doc = doc_repository.get_document(request.document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{request.document_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(request.document_id)
    logger.info("Generating remediation playbook for '%s' with %d findings", request.document_id, len(findings))

    playbook = remediation_engine.generate_playbook(
        document_id=request.document_id,
        findings=findings,
        parsed_doc=doc,
        target_completion_days=request.target_completion_days or 30,
    )
    return playbook


@router.get(
    "/document/{doc_id}",
    response_model=RemediationPlaybook,
    status_code=status.HTTP_200_OK,
)
async def get_document_remediation_playbook(doc_id: str):
    """Retrieves existing remediation playbook for a document or generates one on-demand."""
    pb = remediation_engine.get_playbook_by_document(doc_id)
    if pb:
        return pb

    doc = doc_repository.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found.",
        )

    findings = findings_repository.get_findings_for_document(doc_id)
    return remediation_engine.generate_playbook(
        document_id=doc_id,
        findings=findings,
        parsed_doc=doc,
    )


@router.get(
    "/{playbook_id}",
    response_model=RemediationPlaybook,
    status_code=status.HTTP_200_OK,
)
async def get_playbook(playbook_id: str):
    """Fetches a specific remediation playbook by ID."""
    pb = remediation_engine.get_playbook(playbook_id)
    if not pb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook '{playbook_id}' not found.",
        )
    return pb


@router.patch(
    "/{playbook_id}/action/{action_id}",
    response_model=RemediationActionItem,
    status_code=status.HTTP_200_OK,
)
async def update_action_item_status(
    playbook_id: str,
    action_id: str,
    request: RemediationStatusUpdateRequest,
):
    """Updates the status and notes of a specific remediation action item."""
    item = remediation_engine.update_action_status(
        playbook_id=playbook_id,
        action_id=action_id,
        new_status=request.status,
        notes=request.notes,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_id}' in playbook '{playbook_id}' not found.",
        )
    return item
