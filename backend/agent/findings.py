import json
import os
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.evidence.verifier import EvidenceSpan
from backend.rules.models import RuleType, Severity, Verdict


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"finding-{uuid.uuid4().hex[:10]}")
    document_id: str
    rule_id: str
    rule_code: str
    rule_name: str
    rule_type: RuleType
    verdict: Verdict
    severity: Severity
    evidence: EvidenceSpan | None = None
    reasoning: str
    recommended_action: str
    confidence: float
    searches_run: list[str] = Field(default_factory=list)
    rule_set_version: str = "1.0.0"
    model_used: str = "gpt-4o-mini"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    reviewer_status: str = "pending"  # pending, confirmed, overridden, not_applicable
    reviewer_override_reason: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class FindingsRepository:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self._cache: dict[str, list[Finding]] = {}
        self._all_findings_by_id: dict[str, Finding] = {}

    def save_findings(self, document_id: str, findings: list[Finding]) -> list[Finding]:
        self._cache[document_id] = findings
        for f in findings:
            self._all_findings_by_id[f.id] = f

        doc_dir = os.path.join(self.base_dir, document_id)
        os.makedirs(doc_dir, exist_ok=True)
        findings_path = os.path.join(doc_dir, "findings.json")
        with open(findings_path, "w", encoding="utf-8") as f:
            dump_data = [f.model_dump() for f in findings]
            json.dump(dump_data, f, indent=2)
        return findings

    def get_findings_for_document(self, document_id: str) -> list[Finding]:
        if document_id in self._cache:
            return self._cache[document_id]

        findings_path = os.path.join(self.base_dir, document_id, "findings.json")
        if os.path.exists(findings_path):
            try:
                with open(findings_path, encoding="utf-8") as f:
                    data = json.load(f)
                    findings = [Finding.model_validate(item) for item in data]
                    self._cache[document_id] = findings
                    for f in findings:
                        self._all_findings_by_id[f.id] = f
                    return findings
            except Exception:
                pass
        return []

    def get_finding_by_id(self, finding_id: str) -> Finding | None:
        if finding_id in self._all_findings_by_id:
            return self._all_findings_by_id[finding_id]
        # Search all document folders on disk if not in cache
        if os.path.exists(self.base_dir):
            for entry in os.listdir(self.base_dir):
                doc_path = os.path.join(self.base_dir, entry, "findings.json")
                if os.path.exists(doc_path):
                    self.get_findings_for_document(entry)
                    if finding_id in self._all_findings_by_id:
                        return self._all_findings_by_id[finding_id]
        return None

    def update_finding(
        self, finding_id: str, reviewer_status: str, override_reason: str | None = None, reviewed_by: str | None = None
    ) -> Finding | None:
        finding = self.get_finding_by_id(finding_id)
        if not finding:
            return None

        finding.reviewer_status = reviewer_status
        finding.reviewer_override_reason = override_reason
        finding.reviewed_by = reviewed_by or "compliance_reviewer"
        finding.reviewed_at = datetime.now(UTC).isoformat()

        doc_findings = self.get_findings_for_document(finding.document_id)
        self.save_findings(finding.document_id, doc_findings)
        return finding


findings_repository = FindingsRepository()
