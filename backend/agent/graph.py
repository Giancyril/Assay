import re
import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from backend.agent.state import ComplianceCheckState
from backend.agent.judge import judge_candidate_clause
from backend.rules.precheck import run_deterministic_precheck
from backend.evidence.verifier import verify_quote_in_page_text
from backend.indexing.service import clause_index_service
from backend.ingestion.repository import doc_repository
from backend.rules.models import Verdict


def precheck_node(state: ComplianceCheckState) -> Dict[str, Any]:
    """
    Runs deterministic pre-checks on full document text.
    For PROHIBITED_TERM and NUMERIC_THRESHOLD rules the precheck is authoritative.
    Sets precheck_result and, if deterministic, pre-populates verdict fields so the
    judge_node can confirm or the verify_node can resolve evidence.
    """
    precheck = run_deterministic_precheck(state.full_document_text, state.rule)

    if precheck.has_deterministic_verdict:
        return {
            "precheck_result": precheck,
            "verdict": precheck.verdict,
            "verbatim_quote": precheck.evidence_quote,
            "reasoning": precheck.reasoning or "",
            "recommended_action": (
                f"Strike or amend the violating clause for rule {state.rule.code} ({state.rule.name})."
                if precheck.verdict == Verdict.VIOLATION
                else "No action required."
            ),
            "confidence": precheck.confidence,
            "iteration_count": state.iteration_count + 1
        }

    return {
        "precheck_result": None,
        "iteration_count": state.iteration_count + 1
    }


def should_skip_retrieval(state: ComplianceCheckState) -> str:
    """
    Route directly to verify when precheck produced a deterministic verdict.
    Route to retrieve otherwise (required_clause checks, conditional checks).
    """
    if state.precheck_result is not None and state.precheck_result.has_deterministic_verdict:
        return "verify"
    return "retrieve"


def retrieve_node(state: ComplianceCheckState) -> Dict[str, Any]:
    """
    Multi-phrasing hybrid retrieval for required/conditional clause presence checks.
    Records all searches run so absence can be audited.
    """
    queries = state.rule.search_queries or [state.rule.name, state.rule.description]
    all_chunks = []
    seen_ids = set()
    searches_run = list(state.searches_run)

    for q in queries[:state.max_iterations]:
        searches_run.append(f"hybrid_search('{q}')")
        results = clause_index_service.search_document(
            doc_id=state.document_id,
            query=q,
            top_k=2
        )
        for r in results:
            if r.chunk.id not in seen_ids:
                seen_ids.add(r.chunk.id)
                all_chunks.append(r.chunk)

    return {
        "retrieved_chunks": all_chunks,
        "searches_run": searches_run,
        "iteration_count": state.iteration_count + 1
    }


def judge_node(state: ComplianceCheckState) -> Dict[str, Any]:
    """
    Judges candidate text against compliance rule.
    First re-runs precheck on candidate text (in case the prohibited term lives in
    a specific retrieved chunk), then falls back to heuristic/LLM judge.
    """
    candidate_text = "\n\n".join(c.content for c in state.retrieved_chunks)

    # Re-run precheck on candidate text to catch PROHIBITED_TERM / NUMERIC violations
    # in the retrieved portion (handles cases where precheck on full doc found nothing
    # but retrieved chunk contains the exact violation pattern)
    local_precheck = run_deterministic_precheck(candidate_text, state.rule)
    if local_precheck.has_deterministic_verdict:
        return {
            "verdict": local_precheck.verdict,
            "verbatim_quote": local_precheck.evidence_quote,
            "reasoning": local_precheck.reasoning or "",
            "recommended_action": (
                f"Strike or amend the violating clause for rule {state.rule.code}."
                if local_precheck.verdict == Verdict.VIOLATION
                else "No action required."
            ),
            "confidence": local_precheck.confidence,
            "iteration_count": state.iteration_count + 1
        }

    # LLM / heuristic judgment
    verdict_obj = judge_candidate_clause(state.rule, candidate_text)

    return {
        "verdict": verdict_obj.verdict,
        "verbatim_quote": verdict_obj.verbatim_quote,
        "reasoning": verdict_obj.reasoning,
        "recommended_action": verdict_obj.recommended_action,
        "confidence": verdict_obj.confidence,
        "iteration_count": state.iteration_count + 1
    }


def verify_node(state: ComplianceCheckState) -> Dict[str, Any]:
    """
    Deterministic evidence gate: confirms verbatim quote exists in the source document.
    Rejected quotes (hallucinations) route verdict to needs_review.
    """
    quote = state.verbatim_quote
    doc = doc_repository.get_document(state.document_id)

    if not quote or not doc:
        return {
            "evidence_verified": False,
            "requires_human_review": state.verdict == Verdict.NEEDS_REVIEW,
            "iteration_count": state.iteration_count + 1
        }

    for page in doc.pages:
        verified, span = verify_quote_in_page_text(
            verbatim_quote=quote,
            page_text=page.text,
            page_number=page.page_number,
            char_offset_in_doc=page.char_start_doc
        )
        if verified and span:
            return {
                "verbatim_quote": span.verbatim_quote,
                "page_number": span.page_number,
                "char_start": span.char_start,
                "char_end": span.char_end,
                "evidence_verified": True,
                "rejection_reason": None,
                "iteration_count": state.iteration_count + 1
            }

    # Quote not found in source — hallucination rejection
    return {
        "evidence_verified": False,
        "rejection_reason": "Verbatim quote not found in source document text (rejected)",
        "verdict": Verdict.NEEDS_REVIEW,
        "reasoning": f"Evidence quote could not be verified in source. Original assessment: {state.reasoning}",
        "requires_human_review": True,
        "iteration_count": state.iteration_count + 1
    }


def record_finding_node(state: ComplianceCheckState) -> Dict[str, Any]:
    """Generates a stable finding ID and computes requires_human_review flag."""
    fid = f"finding-{uuid.uuid4().hex[:10]}"
    requires_review = (
        state.verdict == Verdict.NEEDS_REVIEW
        or state.confidence < 0.70
        or (not state.evidence_verified and state.verdict != Verdict.COMPLIANT)
    )
    return {
        "finding_id": fid,
        "requires_human_review": requires_review
    }


def build_compliance_check_graph():
    """Compiles the LangGraph compliance check graph."""
    graph = StateGraph(ComplianceCheckState)

    graph.add_node("precheck", precheck_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("judge", judge_node)
    graph.add_node("verify", verify_node)
    graph.add_node("record", record_finding_node)

    graph.set_entry_point("precheck")

    graph.add_conditional_edges(
        "precheck",
        should_skip_retrieval,
        {
            "verify": "verify",
            "retrieve": "retrieve"
        }
    )

    graph.add_edge("retrieve", "judge")
    graph.add_edge("judge", "verify")
    graph.add_edge("verify", "record")
    graph.add_edge("record", END)

    return graph.compile()


compliance_graph = build_compliance_check_graph()
