import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from backend.rules.models import Verdict, Severity, RuleType
from backend.evidence.verifier import EvidenceSpan
from backend.app.config import settings


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"finding-{uuid.uuid4().hex[:10]}")
    document_id: str
    rule_id: str
    rule_code: str
    rule_name: str
    rule_type: RuleType
    verdict: Verdict
    severity: Severity
    evidence: Optional[EvidenceSpan] = None
    reasoning: str
    recommended_action: str
    confidence: float
    searches_run: List[str] = Field(default_factory=list)
    rule_set_version: str = "1.0.0"
    model_used: str = "gpt-4o-mini"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reviewer_status: str = "pending"  # pending, confirmed, overridden, not_applicable
    reviewer_override_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class FindingsRepository:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self._cache: Dict[str, List[Finding]] = {}
        self._all_findings_by_id: Dict[str, Finding] = {}

    def save_findings(self, document_id: str, findings: List[Finding]) -> List[Finding]:
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

    def get_findings_for_document(self, document_id: str) -> List[Finding]:
        if document_id in self._cache:
            return self._cache[document_id]

        findings_path = os.path.join(self.base_dir, document_id, "findings.json")
        if os.path.exists(findings_path):
            try:
                with open(findings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    findings = [Finding.model_validate(item) for item in data]
                    self._cache[document_id] = findings
                    for f in findings:
                        self._all_findings_by_id[f.id] = f
                    return findings
            except Exception:
                pass
        return []

    def get_finding_by_id(self, finding_id: str) -> Optional[Finding]:
        return self._all_findings_by_id.get(finding_id)


findings_repository = FindingsRepository()
