"""
API router for Feature 3: Real-Time SSE Audit Streaming.

The /api/stream/{doc_id}/audit endpoint opens a Server-Sent Events channel
and runs the compliance check in streaming mode, emitting live progress
events as each rule is evaluated. The frontend connects with EventSource
to render a live progress bar and append findings as they arrive.
"""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.streaming.sse import stream_compliance_check

router = APIRouter(prefix="/api/stream", tags=["SSE Audit Streaming"])


@router.get("/{doc_id}/audit")
async def stream_audit(
    doc_id: str,
    ruleset_id: str = Query(default="ruleset-nda-commercial"),
    ruleset_version: str | None = Query(default=None),
    max_concurrency: int = Query(default=4, ge=1, le=8),
):
    """
    Stream real-time compliance audit progress via Server-Sent Events.

    Connect with `EventSource('/api/stream/{doc_id}/audit')` in the browser.

    Event types emitted:
      - **start**: Audit begun, total rule count included
      - **rule_start**: Named rule is being evaluated
      - **rule_complete**: Rule evaluated — includes full Finding payload
      - **rule_error**: Rule evaluation failed (non-fatal, audit continues)
      - **complete**: All rules evaluated, summary counts included
      - **error**: Fatal stream error

    Each event carries: type, timestamp, rule_code, finding (on complete),
    progress (0.0–1.0), and a human-readable message.
    """
    generator = stream_compliance_check(
        document_id=doc_id,
        ruleset_id=ruleset_id,
        ruleset_version=ruleset_version,
        max_concurrency=max_concurrency,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
            "Connection": "keep-alive",
        },
    )
