import uuid
from datetime import UTC, datetime
from typing import Optional

from backend.agent.findings import Finding
from backend.ingestion.models import ParsedDocument
from backend.remediation.models import (
    RemediationActionItem,
    RemediationActionType,
    RemediationPlaybook,
    RemediationPriority,
    RemediationStatus,
)


CLAUSE_TEMPLATES = {
    "confidentiality": (
        "Confidentiality Term Clause:\n"
        "Each party's confidentiality obligations under this Agreement shall survive termination "
        "and continue in full force and effect for a period of three (3) years from the date of disclosure; "
        "provided, however, that trade secrets shall be maintained in confidence for so long as they remain trade secrets under applicable law."
    ),
    "liability": (
        "Limitation of Liability Clause:\n"
        "Except for gross negligence or willful misconduct, in no event shall either party's aggregate liability "
        "arising out of or related to this Agreement exceed the total fees paid or payable by Customer in the twelve (12) months preceding the incident."
    ),
    "breach_notification": (
        "Security Incident & Breach Notification Clause:\n"
        "Vendor shall notify Customer in writing without undue delay and in any event within seventy-two (72) hours "
        "of becoming aware of any confirmed Security Incident or Personal Data Breach affecting Customer Data."
    ),
    "audit_rights": (
        "Audit and Inspection Clause:\n"
        "Upon at least ten (10) business days prior written notice, Customer or its designated independent certified auditor "
        "shall have the right to inspect and audit Vendor's operational facilities, security practices, and compliance records."
    ),
    "termination": (
        "Termination for Cause and Convenience:\n"
        "Either party may terminate this Agreement immediately upon written notice if the other party materially breaches "
        "any provision and fails to cure within thirty (30) days of receiving written notice."
    ),
    "data_protection": (
        "Data Protection & Subprocessor Clause:\n"
        "Vendor shall process Customer Personal Data strictly in accordance with Customer's documented instructions "
        "and shall not engage sub-processors without Customer's prior written consent."
    ),
}


class RemediationPlaybookEngine:
    """Automated engine to synthesize compliance findings into actionable remediation roadmaps."""

    def __init__(self):
        self._playbooks: dict[str, RemediationPlaybook] = {}

    def generate_playbook(
        self,
        document_id: str,
        findings: list[Finding],
        parsed_doc: Optional[ParsedDocument] = None,
        target_completion_days: int = 30,
    ) -> RemediationPlaybook:
        """Synthesizes compliance findings into a structured, prioritized remediation playbook."""
        items: list[RemediationActionItem] = []
        doc_text = parsed_doc.text.lower() if parsed_doc and parsed_doc.text else ""

        for finding in findings:
            # Only generate remediation for non-compliant or warning findings
            status_val = getattr(finding.status, "value", str(finding.status)).lower()
            if status_val not in ["failed", "fail", "non_compliant", "warning", "warn"]:
                continue

            rule_id = finding.rule_id
            finding_text = f"{finding.rule_title} {finding.explanation}".lower()

            # Determine action type, role, and clause template
            if "liability" in finding_text or "indemnif" in finding_text:
                action_type = RemediationActionType.CONTRACT_AMENDMENT
                priority = RemediationPriority.CRITICAL
                sla_days = min(7, target_completion_days)
                role = "Chief Legal Counsel"
                suggested_clause = CLAUSE_TEMPLATES["liability"]
                title = f"Cap Aggregate Liability and Clarify Indemnification ({rule_id})"
                desc = (
                    "Negotiate a balanced mutual limitation of liability cap tied to trailing 12-month contract value "
                    "and remove unlimited indemnity triggers."
                )
            elif "confidential" in finding_text or "perpetual" in finding_text:
                action_type = RemediationActionType.CONTRACT_AMENDMENT
                priority = RemediationPriority.HIGH
                sla_days = min(14, target_completion_days)
                role = "Commercial Contracts Lead"
                suggested_clause = CLAUSE_TEMPLATES["confidentiality"]
                title = f"Replace Perpetual Confidentiality with Fixed Term ({rule_id})"
                desc = (
                    "Amend survival clause to limit standard confidential information obligations to 3-5 years, "
                    "with perpetual carveout strictly restricted to bona fide trade secrets."
                )
            elif "breach" in finding_text or "incident" in finding_text or "72" in finding_text:
                action_type = RemediationActionType.TECHNICAL_CONTROL
                priority = RemediationPriority.CRITICAL
                sla_days = min(5, target_completion_days)
                role = "Data Protection Officer"
                suggested_clause = CLAUSE_TEMPLATES["breach_notification"]
                title = f"Enforce 72-Hour Security Incident Escalation Protocol ({rule_id})"
                desc = (
                    "Institute automated incident escalation procedures to guarantee written breach notification "
                    "within 72 hours in compliance with GDPR Art. 33."
                )
            elif "audit" in finding_text or "inspection" in finding_text:
                action_type = RemediationActionType.VENDOR_NEGOTIATION
                priority = RemediationPriority.MEDIUM
                sla_days = min(21, target_completion_days)
                role = "Vendor Risk Management Lead"
                suggested_clause = CLAUSE_TEMPLATES["audit_rights"]
                title = f"Secure Formal Right-to-Audit Provisions ({rule_id})"
                desc = (
                    "Execute bilateral addendum guaranteeing annual independent third-party audit rights "
                    "and SOC 2 Type II report access."
                )
            elif "subprocessor" in finding_text or "gdpr" in finding_text or "personal data" in finding_text:
                action_type = RemediationActionType.POLICY_UPDATE
                priority = RemediationPriority.HIGH
                sla_days = min(14, target_completion_days)
                role = "Privacy Compliance Officer"
                suggested_clause = CLAUSE_TEMPLATES["data_protection"]
                title = f"Implement Data Processing Addendum (DPA) ({rule_id})"
                desc = (
                    "Execute standard Data Processing Agreement incorporating formal subprocessor notification "
                    "and opt-out mechanisms."
                )
            else:
                action_type = RemediationActionType.PROCESS_CHANGE
                priority = RemediationPriority.MEDIUM
                sla_days = min(20, target_completion_days)
                role = "Compliance Operations Manager"
                suggested_clause = None
                title = f"Review and Correct Compliance Deviation ({rule_id})"
                desc = f"Address identified non-compliance in rule '{finding.rule_title}': {finding.explanation}"

            action_item = RemediationActionItem(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                rule_id=rule_id,
                finding_id=finding.finding_id,
                title=title,
                description=desc,
                action_type=action_type,
                priority=priority,
                sla_days=sla_days,
                suggested_clause=suggested_clause,
                rationale=finding.explanation,
                responsible_role=role,
                status=RemediationStatus.PENDING,
            )
            items.append(action_item)

        # Count priorities
        crit = sum(1 for i in items if i.priority == RemediationPriority.CRITICAL)
        high = sum(1 for i in items if i.priority == RemediationPriority.HIGH)
        med = sum(1 for i in items if i.priority == RemediationPriority.MEDIUM)
        low = sum(1 for i in items if i.priority == RemediationPriority.LOW)

        # Estimated duration is driven by highest SLA or max days
        est_days = max([i.sla_days for i in items], default=0)

        playbook_id = f"pb-{uuid.uuid4().hex[:8]}"
        summary = (
            f"Remediation Roadmap generated with {len(items)} action items "
            f"({crit} Critical, {high} High, {med} Medium, {low} Low). "
            f"Projected full resolution time: {est_days} business days."
        )

        playbook = RemediationPlaybook(
            playbook_id=playbook_id,
            document_id=document_id,
            created_at=datetime.now(UTC),
            total_actions=len(items),
            critical_actions_count=crit,
            high_actions_count=high,
            medium_actions_count=med,
            low_actions_count=low,
            estimated_remediation_days=est_days,
            items=items,
            summary=summary,
        )

        self._playbooks[playbook_id] = playbook
        return playbook

    def get_playbook(self, playbook_id: str) -> Optional[RemediationPlaybook]:
        return self._playbooks.get(playbook_id)

    def get_playbook_by_document(self, document_id: str) -> Optional[RemediationPlaybook]:
        for pb in reversed(list(self._playbooks.values())):
            if pb.document_id == document_id:
                return pb
        return None

    def update_action_status(
        self,
        playbook_id: str,
        action_id: str,
        new_status: RemediationStatus,
        notes: Optional[str] = None,
    ) -> Optional[RemediationActionItem]:
        pb = self._playbooks.get(playbook_id)
        if not pb:
            return None
        for item in pb.items:
            if item.action_id == action_id:
                item.status = new_status
                if new_status == RemediationStatus.RESOLVED:
                    item.completed_at = datetime.now(UTC)
                if notes:
                    item.description = f"{item.description}\n[Status Note]: {notes}"
                return item
        return None


remediation_engine = RemediationPlaybookEngine()
