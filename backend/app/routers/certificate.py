"""
API router for Feature 5: Cryptographic Audit Certificate & Verification.

Issues tamper-evident audit certificates for completed compliance checks and
exposes a verification endpoint so third parties can confirm authenticity
without possessing the HMAC key (via the public payload_sha256).
"""
from fastapi import APIRouter, HTTPException, status

from backend.certificate.generator import AuditCertificate, generate_certificate, verify_certificate

router = APIRouter(prefix="/api/certificates", tags=["Audit Certificates"])


@router.post("/verify", response_model=dict)
async def verify_audit_certificate(cert: AuditCertificate):
    """
    Verify the HMAC integrity of an audit certificate.

    Returns `{"valid": true, "certificate_id": "..."}` if authentic,
    or `{"valid": false, "reason": "..."}` if the certificate has been tampered with.
    """
    is_valid = verify_certificate(cert)
    if is_valid:
        return {
            "valid": True,
            "certificate_id": cert.certificate_id,
            "issued_at": cert.issued_at,
            "document_id": cert.document_id,
            "overall_status": cert.overall_status,
            "message": "Certificate integrity verified - payload has not been tampered with.",
        }
    return {
        "valid": False,
        "certificate_id": cert.certificate_id,
        "reason": "HMAC signature mismatch - certificate payload has been modified after issuance.",
    }

@router.post("/{doc_id}", response_model=AuditCertificate, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    doc_id: str,
    ruleset_id: str = "ruleset-nda-commercial",
    ruleset_version: str = "1.0.0",
):
    """
    Issue a cryptographic audit certificate for a completed compliance check.

    The certificate contains:
    - Document metadata and SHA-256 hash of extracted text
    - Compliance summary (score, status, per-verdict counts)
    - All finding records (id, rule, verdict, severity)
    - An HMAC-SHA256 integrity signature over the canonical payload

    **Tamper detection**: Any modification to the certificate payload will
    invalidate the `hmac_signature` and can be detected via the `/verify` endpoint.
    """
    try:
        cert = generate_certificate(
            document_id=doc_id,
            ruleset_id=ruleset_id,
            ruleset_version=ruleset_version,
        )
        return cert
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


