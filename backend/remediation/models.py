from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RemediationPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RemediationStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"
    ESCALATED = "ESCALATED"


class RemediationActionType(StrEnum):
    CONTRACT_AMENDMENT = "CONTRACT_AMENDMENT"
    POLICY_UPDATE = "POLICY_UPDATE"
    TECHNICAL_CONTROL = "TECHNICAL_CONTROL"
    PROCESS_CHANGE = "PROCESS_CHANGE"
    VENDOR_NEGOTIATION = "VENDOR_NEGOTIATION"


class RemediationActionItem(BaseModel):
    action_id: str = Field(..., description="Unique identifier for the action item")
    rule_id: str = Field(..., description="Target rule ID that triggered this remediation")
    finding_id: str = Field(..., description="Associated compliance finding ID")
    title: str = Field(..., description="Concise title of the remediation task")
    description: str = Field(..., description="Detailed instructions for resolving the issue")
    action_type: RemediationActionType = Field(..., description="Type of remediation required")
    priority: RemediationPriority = Field(..., description="Remediation urgency and priority")
    sla_days: int = Field(default=14, description="Target turnaround SLA in business days")
    suggested_clause: str | None = Field(default=None, description="Drafted amendment clause text")
    rationale: str = Field(..., description="Legal or compliance justification")
    responsible_role: str = Field(..., description="Organizational owner responsible for execution")
    status: RemediationStatus = Field(default=RemediationStatus.PENDING, description="Current status")
    completed_at: datetime | None = Field(default=None, description="Resolution timestamp")


class RemediationPlaybook(BaseModel):
    playbook_id: str = Field(..., description="Unique playbook identifier")
    document_id: str = Field(..., description="Document or contract analyzed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_actions: int = Field(default=0)
    critical_actions_count: int = Field(default=0)
    high_actions_count: int = Field(default=0)
    medium_actions_count: int = Field(default=0)
    low_actions_count: int = Field(default=0)
    estimated_remediation_days: int = Field(default=14)
    items: list[RemediationActionItem] = Field(default_factory=list)
    summary: str = Field(..., description="Executive summary of the remediation roadmap")


class RemediationGenerateRequest(BaseModel):
    document_id: str = Field(..., description="Document ID to generate remediation plan for")
    target_completion_days: int | None = Field(default=30, description="Desired remediation window")


class RemediationStatusUpdateRequest(BaseModel):
    status: RemediationStatus = Field(..., description="New remediation status")
    notes: str | None = Field(default=None, description="Resolution notes or waiver justification")
