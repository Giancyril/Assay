import asyncio

from fastapi import HTTPException, status

from backend.agent.findings import Finding, findings_repository
from backend.agent.graph import compliance_graph
from backend.agent.state import ComplianceCheckState
from backend.evidence.verifier import EvidenceSpan
from backend.ingestion.repository import doc_repository
from backend.rules.engine import rule_engine
from backend.rules.models import ComplianceRule, Verdict


async def execute_single_rule_check(
    document_id: str, full_text: str, rule: ComplianceRule, rule_set_version: str = "1.0.0"
) -> Finding:
    """Executes the LangGraph check graph for one (document, rule) pair."""
    initial_state = ComplianceCheckState(
        document_id=document_id, rule_id=rule.id, rule=rule, full_document_text=full_text, max_iterations=3
    )

    # Run graph (CPU-bound / async friendly)
    result_dict = await asyncio.to_thread(compliance_graph.invoke, initial_state)

    # Extract final fields
    verdict = result_dict.get("verdict") or Verdict.NEEDS_REVIEW
    quote = result_dict.get("verbatim_quote")
    evidence_verified = result_dict.get("evidence_verified", False)
    page_num = result_dict.get("page_number")
    c_start = result_dict.get("char_start")
    c_end = result_dict.get("char_end")

    evidence_span = None
    if quote and evidence_verified and page_num is not None:
        evidence_span = EvidenceSpan(
            verbatim_quote=quote,
            page_number=page_num,
            char_start=c_start or 0,
            char_end=c_end or len(quote),
            verified=True,
        )

    finding = Finding(
        id=result_dict.get("finding_id") or f"finding-{rule.code.lower()}",
        document_id=document_id,
        rule_id=rule.id,
        rule_code=rule.code,
        rule_name=rule.name,
        rule_type=rule.rule_type,
        verdict=verdict,
        severity=rule.severity,
        evidence=evidence_span,
        reasoning=result_dict.get("reasoning") or "",
        recommended_action=result_dict.get("recommended_action") or "",
        confidence=result_dict.get("confidence", 0.8),
        searches_run=result_dict.get("searches_run", []),
        rule_set_version=rule_set_version,
    )
    return finding


async def check_document_against_ruleset(
    document_id: str,
    ruleset_id: str = "ruleset-nda-commercial",
    ruleset_version: str | None = None,
    max_concurrency: int = 4,
    rule_codes: list[str] | None = None,
) -> list[Finding]:
    """
    Runs compliance checks in parallel across all rules in a ruleset.
    Bounded by concurrency limit to manage resource usage.
    """
    doc = doc_repository.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{document_id}' not found.")

    ruleset = rule_engine.get_rule_set(ruleset_id, version=ruleset_version)
    active_rules = ruleset.rules
    if rule_codes:
        active_rules = [r for r in active_rules if r.code in rule_codes]

    semaphore = asyncio.Semaphore(max_concurrency)

    async def sem_check(rule: ComplianceRule) -> Finding:
        async with semaphore:
            retries = 2
            while retries >= 0:
                try:
                    return await execute_single_rule_check(
                        document_id=doc.id, full_text=doc.full_text, rule=rule, rule_set_version=ruleset.version
                    )
                except Exception as e:
                    retries -= 1
                    if retries < 0:
                        # Fallback error finding
                        return Finding(
                            document_id=doc.id,
                            rule_id=rule.id,
                            rule_code=rule.code,
                            rule_name=rule.name,
                            rule_type=rule.rule_type,
                            verdict=Verdict.NEEDS_REVIEW,
                            severity=rule.severity,
                            reasoning=f"Check failed due to internal error: {e!s}",
                            recommended_action="Retry rule check manually.",
                            confidence=0.0,
                            rule_set_version=ruleset.version,
                        )
                    await asyncio.sleep(0.5)

    tasks = [sem_check(rule) for rule in active_rules]
    findings = await asyncio.gather(*tasks)

    # Save findings
    findings_repository.save_findings(document_id, list(findings))
    return list(findings)
