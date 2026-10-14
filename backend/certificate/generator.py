"""
Feature 5: Cryptographic Audit Certificate & Verification.

Generates a tamper-evident audit certificate for a completed compliance check.
The certificate is a JSON document containing:

  - Document metadata (id, filename, SHA-256 hash of extracted text)
  - Ruleset used (id, version)
  - Compliance summary (score, overall status, per-verdict counts)
  - All finding IDs, verdicts, and severities
  - Issuer information and timestamp
  - A SHA-256 HMAC integrity signature over the canonical payload

Verification: Any party with the shared HMAC secret can re-compute the
signature and confirm the certificate has not been altered after issuance.
In production this secret should be an asymmetric signing key (RSA/ECDSA);
HMAC is used here as a zero-dependency approach that works without a PKI.
"""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.agent.findings import findings_repository
from backend.app.config import settings
from backend.ingestion.repository import doc_repository

# HMAC key — in production, inject via environment variable; fall back to project secret.
_HMAC_KEY: bytes = (getattr(settings, "AUDIT_HMAC_SECRET", None) or settings.SECRET_KEY).encode("utf-8")


class FindingCertRecord(BaseModel):
    finding_id: str
    rule_code: str
    rule_name: str
    verdict: str
    severity: str
    reviewer_status: str


class AuditCertificate(BaseModel):
    """
    Tamper-evident audit certificate for a compliance check session.
    """

    certificate_id: str = Field(default_factory=lambda: f"cert-{uuid.uuid4().hex}")
    issued_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    issuer: str = "Compliance Agent Automated Audit System v1"

    # Document
    document_id: str
    document_filename: str
    document_text_sha256: str  # SHA-256 of extracted text for tamper detection

    # Ruleset
    ruleset_id: str
    ruleset_version: str

    # Summary
    total_findings: int
    compliance_score: float
    overall_status: str
    counts: dict[str, int]

    # Finding records (lightweight, not full finding)
    findings: list[FindingCertRecord]

    # Integrity
    payload_sha256: str  # SHA-256 of canonical JSON payload (excluding this field)
    hmac_signature: str  # HMAC-SHA256(payload_sha256, _HMAC_KEY) as hex digest
    verified: bool = False  # Set to True after caller verifies


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _hmac_sign(payload_hash: str) -> str:
    return hmac.new(_HMAC_KEY, payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _canonical_payload(cert: dict[str, Any]) -> str:
    """Produce deterministic JSON excluding integrity fields for signing."""
    excluded = {"payload_sha256", "hmac_signature", "verified"}
    clean = {k: v for k, v in cert.items() if k not in excluded}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"))


def generate_certificate(
    document_id: str,
    ruleset_id: str = "ruleset-nda-commercial",
    ruleset_version: str = "1.0.0",
) -> AuditCertificate:
    """
    Issue a cryptographic audit certificate for a completed compliance check.

    Raises ValueError if the document or findings are not found.
    """
    doc = doc_repository.get_document(document_id)
    if not doc:
        raise ValueError(f"Document '{document_id}' not found.")

    findings = findings_repository.get_findings_for_document(document_id)
    if not findings:
        raise ValueError(f"No findings for document '{document_id}'. Run a compliance check first.")

    # Document text hash
    text_hash = _sha256(doc.full_text or "")

    # Counts
    total = len(findings)
    violations = sum(1 for f in findings if str(f.verdict) == "violation")
    needs_review = sum(1 for f in findings if str(f.verdict) == "needs_review")
    compliant = sum(1 for f in findings if str(f.verdict) == "compliant")
    not_app = sum(1 for f in findings if str(f.verdict) == "not_applicable")
    score = round(compliant / total * 100, 1) if total > 0 else 0.0

    if violations > 0:
        overall_status = "NON_COMPLIANT"
    elif needs_review > 0:
        overall_status = "REQUIRES_REVIEW"
    else:
        overall_status = "COMPLIANT"

    finding_records = [
        FindingCertRecord(
            finding_id=f.id,
            rule_code=f.rule_code,
            rule_name=f.rule_name,
            verdict=str(f.verdict),
            severity=str(f.severity),
            reviewer_status=f.reviewer_status,
        )
        for f in findings
    ]

    # Build certificate (without integrity fields yet)
    cert_data = {
        "certificate_id": f"cert-{uuid.uuid4().hex}",
        "issued_at": datetime.now(UTC).isoformat(),
        "issuer": "Compliance Agent Automated Audit System v1",
        "document_id": document_id,
        "document_filename": doc.filename,
        "document_text_sha256": text_hash,
        "ruleset_id": ruleset_id,
        "ruleset_version": ruleset_version,
        "total_findings": total,
        "compliance_score": score,
        "overall_status": overall_status,
        "counts": {
            "violation": violations,
            "needs_review": needs_review,
            "compliant": compliant,
            "not_applicable": not_app,
        },
        "findings": [r.model_dump() for r in finding_records],
    }

    # Compute integrity signature
    canonical = _canonical_payload(cert_data)
    payload_hash = _sha256(canonical)
    signature = _hmac_sign(payload_hash)

    cert_data["payload_sha256"] = payload_hash
    cert_data["hmac_signature"] = signature
    cert_data["verified"] = False

    return AuditCertificate.model_validate(cert_data)


def verify_certificate(cert: AuditCertificate) -> bool:
    """
    Verify a certificate's HMAC integrity signature.

    Returns True if the certificate is authentic and unmodified.
    """
    cert_dict = cert.model_dump()
    canonical = _canonical_payload(cert_dict)
    expected_hash = _sha256(canonical)
    expected_sig = _hmac_sign(expected_hash)

    hash_match = hmac.compare_digest(expected_hash, cert.payload_sha256)
    sig_match = hmac.compare_digest(expected_sig, cert.hmac_signature)
    return hash_match and sig_match
