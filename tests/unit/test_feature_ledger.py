from fastapi.testclient import TestClient

from backend.app.main import app
from backend.ledger.models import LedgerEventType
from backend.ledger.service import AuditLedgerService

client = TestClient(app)


def test_ledger_genesis_and_chain_append():
    service = AuditLedgerService()
    assert len(service.get_timeline()) == 1

    genesis = service.get_block(0)
    assert genesis is not None
    assert genesis.block_index == 0
    assert genesis.document_id == "genesis"

    # Append block 1
    b1 = service.append_event(
        document_id="doc-101",
        event_type=LedgerEventType.DOCUMENT_INGESTED,
        actor="system:ingest",
        payload={"filename": "master_agreement.pdf", "size": 1024},
    )
    assert b1.block_index == 1
    assert b1.prev_hash == genesis.block_hash

    # Append block 2
    b2 = service.append_event(
        document_id="doc-101",
        event_type=LedgerEventType.AUDIT_INITIATED,
        actor="agent:auditor",
        payload={"ruleset": "enterprise_v1", "rules_count": 8},
    )
    assert b2.block_index == 2
    assert b2.prev_hash == b1.block_hash

    # Verify integrity
    verif = service.verify_integrity()
    assert verif.is_valid is True
    assert verif.total_blocks == 3
    assert verif.tampered_block_index is None


def test_ledger_tamper_detection_payload():
    service = AuditLedgerService()
    service.append_event("doc-202", LedgerEventType.AUDIT_INITIATED, payload={"status": "initial"})
    b2 = service.append_event("doc-202", LedgerEventType.FINDING_RECORDED, payload={"severity": "CRITICAL"})

    # Tamper with block payload directly
    b2.payload["severity"] = "LOW"  # Maliciously altered finding severity

    verif = service.verify_integrity()
    assert verif.is_valid is False
    assert verif.tampered_block_index == 2
    assert "mismatch" in verif.message.lower()


def test_ledger_tamper_detection_prev_hash():
    service = AuditLedgerService()
    service.append_event("doc-303", LedgerEventType.AUDIT_INITIATED)
    b2 = service.append_event("doc-303", LedgerEventType.CERTIFICATE_ISSUED)

    # Corrupt the hash link
    b2.prev_hash = "deadbeef" * 8

    verif = service.verify_integrity()
    assert verif.is_valid is False
    assert verif.tampered_block_index == 2


def test_ledger_api_record_and_timeline():
    # 1. Record event
    payload = {
        "document_id": "doc-api-ledger-test",
        "event_type": "AUDIT_INITIATED",
        "actor": "user:qa_tester",
        "payload": {"test_mode": True},
    }
    res = client.post("/api/ledger/record", json=payload)
    assert res.status_code == 201
    block = res.json()
    assert block["document_id"] == "doc-api-ledger-test"
    assert "block_hash" in block
    assert "prev_hash" in block
    block_idx = block["block_index"]

    # 2. Get block by index
    get_block_res = client.get(f"/api/ledger/block/{block_idx}")
    assert get_block_res.status_code == 200
    assert get_block_res.json()["block_index"] == block_idx

    # 3. Get timeline filtered
    timeline_res = client.get("/api/ledger/timeline?document_id=doc-api-ledger-test")
    assert timeline_res.status_code == 200
    blocks = timeline_res.json()
    assert len(blocks) >= 1
    assert any(b["block_index"] == block_idx for b in blocks)

    # 4. Verify endpoint
    verify_res = client.get("/api/ledger/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["is_valid"] is True


def test_ledger_api_block_not_found():
    res = client.get("/api/ledger/block/9999999")
    assert res.status_code == 404
