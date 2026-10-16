import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from backend.ledger.models import (
    LedgerBlock,
    LedgerEventType,
    LedgerVerificationResult,
)

GENESIS_PREV_HASH = "0" * 64


def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_payload_hash(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return compute_sha256(canonical_json)


def compute_block_hash(
    block_index: int,
    timestamp_iso: str,
    prev_hash: str,
    payload_hash: str,
    event_type: str,
    document_id: str,
    actor: str,
) -> str:
    raw_material = f"{block_index}|{timestamp_iso}|{prev_hash}|{payload_hash}|{event_type}|{document_id}|{actor}"
    return compute_sha256(raw_material)


class AuditLedgerService:
    """Tamper-evident, cryptographically chained audit ledger."""

    def __init__(self):
        self._chain: list[LedgerBlock] = []
        self._initialize_genesis()

    def _initialize_genesis(self):
        genesis_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        time_iso = genesis_time.isoformat()
        payload = {"message": "Genesis Block of Compliance Audit Ledger", "version": "1.0.0"}
        p_hash = compute_payload_hash(payload)
        b_hash = compute_block_hash(
            block_index=0,
            timestamp_iso=time_iso,
            prev_hash=GENESIS_PREV_HASH,
            payload_hash=p_hash,
            event_type=LedgerEventType.DOCUMENT_INGESTED.value,
            document_id="genesis",
            actor="system",
        )
        genesis_block = LedgerBlock(
            block_index=0,
            timestamp=genesis_time,
            event_type=LedgerEventType.DOCUMENT_INGESTED,
            document_id="genesis",
            actor="system",
            payload=payload,
            payload_hash=p_hash,
            prev_hash=GENESIS_PREV_HASH,
            block_hash=b_hash,
        )
        self._chain.append(genesis_block)

    def append_event(
        self,
        document_id: str,
        event_type: LedgerEventType,
        actor: str = "system:compliance_orchestrator",
        payload: dict[str, Any] | None = None,
    ) -> LedgerBlock:
        payload = payload or {}
        now = datetime.now(UTC)
        time_iso = now.isoformat()
        prev_block = self._chain[-1]
        new_index = len(self._chain)

        p_hash = compute_payload_hash(payload)
        b_hash = compute_block_hash(
            block_index=new_index,
            timestamp_iso=time_iso,
            prev_hash=prev_block.block_hash,
            payload_hash=p_hash,
            event_type=event_type.value,
            document_id=document_id,
            actor=actor,
        )

        block = LedgerBlock(
            block_index=new_index,
            timestamp=now,
            event_type=event_type,
            document_id=document_id,
            actor=actor,
            payload=payload,
            payload_hash=p_hash,
            prev_hash=prev_block.block_hash,
            block_hash=b_hash,
        )
        self._chain.append(block)
        return block

    def get_timeline(self, document_id: str | None = None) -> list[LedgerBlock]:
        if document_id:
            return [b for b in self._chain if b.document_id == document_id]
        return list(self._chain)

    def get_block(self, block_index: int) -> LedgerBlock | None:
        if 0 <= block_index < len(self._chain):
            return self._chain[block_index]
        return None

    def verify_integrity(self) -> LedgerVerificationResult:
        """Verifies the complete cryptographic hash chain across all recorded audit blocks."""
        if not self._chain:
            return LedgerVerificationResult(
                is_valid=False,
                total_blocks=0,
                last_block_hash="",
                tampered_block_index=0,
                message="Ledger is empty; genesis block missing.",
            )

        for i, block in enumerate(self._chain):
            # Check genesis block
            if i == 0:
                if block.prev_hash != GENESIS_PREV_HASH:
                    return LedgerVerificationResult(
                        is_valid=False,
                        total_blocks=len(self._chain),
                        last_block_hash=self._chain[-1].block_hash,
                        tampered_block_index=0,
                        message="Genesis block prev_hash invalid.",
                    )
            else:
                # Check link to previous block
                prev_block = self._chain[i - 1]
                if block.prev_hash != prev_block.block_hash:
                    return LedgerVerificationResult(
                        is_valid=False,
                        total_blocks=len(self._chain),
                        last_block_hash=self._chain[-1].block_hash,
                        tampered_block_index=i,
                        message=f"Block {i} prev_hash does not match block {i - 1} block_hash.",
                    )

            # Check payload integrity
            recomputed_p_hash = compute_payload_hash(block.payload)
            if block.payload_hash != recomputed_p_hash:
                return LedgerVerificationResult(
                    is_valid=False,
                    total_blocks=len(self._chain),
                    last_block_hash=self._chain[-1].block_hash,
                    tampered_block_index=i,
                    message=f"Block {i} payload hash mismatch (data tampered).",
                )

            # Check block hash integrity
            recomputed_b_hash = compute_block_hash(
                block_index=block.block_index,
                timestamp_iso=block.timestamp.isoformat(),
                prev_hash=block.prev_hash,
                payload_hash=block.payload_hash,
                event_type=block.event_type.value,
                document_id=block.document_id,
                actor=block.actor,
            )
            if block.block_hash != recomputed_b_hash:
                return LedgerVerificationResult(
                    is_valid=False,
                    total_blocks=len(self._chain),
                    last_block_hash=self._chain[-1].block_hash,
                    tampered_block_index=i,
                    message=f"Block {i} block_hash signature broken.",
                )

        return LedgerVerificationResult(
            is_valid=True,
            total_blocks=len(self._chain),
            last_block_hash=self._chain[-1].block_hash,
            tampered_block_index=None,
            message="Cryptographic audit ledger verified successfully. All block hashes and payload signatures are authentic.",
        )


audit_ledger_service = AuditLedgerService()
