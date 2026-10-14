"""
Feature 3: Real-Time SSE Audit Streaming.

Provides a Server-Sent Events (SSE) stream that emits compliance check
progress events in real time as each rule is evaluated by the LangGraph
agent. The frontend can render a live progress bar and append findings
as they arrive without polling.

Event schema (JSON-encoded data fields):
  - type: "start" | "rule_start" | "rule_complete" | "complete" | "error"
  - rule_code: str (present on rule_* events)
  - finding: Finding dict (present on rule_complete)
  - progress: float 0.0-1.0
  - message: str
  - timestamp: ISO 8601
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from backend.agent.findings import Finding, findings_repository
from backend.agent.orchestrator import check_document_against_ruleset
from backend.rules.engine import rule_engine

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event string."""
    payload = json.dumps({"type": event_type, "timestamp": _now(), **data})
    return f"data: {payload}\n\n"


async def stream_compliance_check(
    document_id: str,
    ruleset_id: str = "ruleset-nda-commercial",
    ruleset_version: str | None = None,
    max_concurrency: int = 4,
) -> AsyncGenerator[str, None]:
    """
    Async generator that runs a compliance check and yields SSE events for each step.

    Emits:
      1. start event with total rule count
      2. rule_start for each rule before evaluation
      3. rule_complete for each rule after the agent responds
      4. complete event with final summary counts
      5. error event on any exception
    """
    try:
        ruleset = rule_engine.get_rule_set(ruleset_id, version=ruleset_version)
        rules = ruleset.rules
        total = len(rules)

        yield _sse_event("start", {
            "document_id": document_id,
            "ruleset_id": ruleset_id,
            "total_rules": total,
            "message": f"Starting compliance audit — {total} rules to evaluate",
            "progress": 0.0,
        })

        # Stream rules one-by-one to give granular progress updates.
        # We run them with concurrency=1 during streaming to provide ordered events;
        # production can switch to batch streaming with a queue approach.
        all_findings: list[Finding] = []

        for idx, rule in enumerate(rules):
            yield _sse_event("rule_start", {
                "rule_code": rule.code,
                "rule_name": rule.name,
                "rule_index": idx + 1,
                "total_rules": total,
                "message": f"Evaluating rule {rule.code}: {rule.name}",
                "progress": round(idx / total, 4),
            })

            # Small yield to allow event loop to flush the SSE buffer
            await asyncio.sleep(0)

            try:
                # Run agent for this specific rule only
                rule_findings = await check_document_against_ruleset(
                    document_id=document_id,
                    ruleset_id=ruleset_id,
                    ruleset_version=ruleset_version,
                    max_concurrency=1,
                    rule_codes=[rule.code],
                )
            except Exception as rule_err:
                logger.warning("Rule %s evaluation failed: %s", rule.code, rule_err)
                yield _sse_event("rule_error", {
                    "rule_code": rule.code,
                    "message": f"Rule {rule.code} evaluation failed: {rule_err}",
                    "progress": round((idx + 1) / total, 4),
                })
                continue

            all_findings.extend(rule_findings)

            for finding in rule_findings:
                yield _sse_event("rule_complete", {
                    "rule_code": rule.code,
                    "rule_name": rule.name,
                    "rule_index": idx + 1,
                    "total_rules": total,
                    "verdict": str(finding.verdict),
                    "severity": str(finding.severity),
                    "finding": finding.model_dump(),
                    "message": f"Rule {rule.code}: {finding.verdict.upper()}",
                    "progress": round((idx + 1) / total, 4),
                })

        # Summarize
        counts = {
            "compliant": sum(1 for f in all_findings if str(f.verdict) == "compliant"),
            "violation": sum(1 for f in all_findings if str(f.verdict) == "violation"),
            "needs_review": sum(1 for f in all_findings if str(f.verdict) == "needs_review"),
            "not_applicable": sum(1 for f in all_findings if str(f.verdict) == "not_applicable"),
        }

        yield _sse_event("complete", {
            "document_id": document_id,
            "total_findings": len(all_findings),
            "counts": counts,
            "message": "Compliance audit complete",
            "progress": 1.0,
        })

    except Exception as exc:
        logger.exception("SSE stream error for document %s: %s", document_id, exc)
        yield _sse_event("error", {
            "document_id": document_id,
            "message": f"Audit stream error: {exc}",
            "progress": 0.0,
        })

