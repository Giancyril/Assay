"""
Visual Highlight Locator — Feature 2: Visual Document Highlighting & Jump-to-Source.

Maps each compliance finding to HighlightAnnotations with page offsets, semantic
colors, tooltip summaries, and PDF jump-links that the frontend can consume to
overlay highlights directly on the rendered document.
"""
from backend.agent.findings import Finding
from backend.highlight.models import (
    DocumentHighlightMap,
    HighlightAnnotation,
    VERDICT_COLOR_MAP,
)
from backend.ingestion.repository import doc_repository


def _build_tooltip(finding: Finding) -> str:
    lines = [
        f"Rule: {finding.rule_code} — {finding.rule_name}",
        f"Verdict: {finding.verdict.upper()}",
        f"Severity: {finding.severity.upper()}",
    ]
    if finding.reasoning:
        # Truncate to 200 chars for tooltip
        excerpt = finding.reasoning[:200]
        if len(finding.reasoning) > 200:
            excerpt += "…"
        lines.append(f"Analysis: {excerpt}")
    if finding.recommended_action:
        lines.append(f"Action: {finding.recommended_action[:150]}")
    return "\n".join(lines)


def _build_jump_url(doc_id: str, finding: Finding) -> str | None:
    """Construct a PDF.js-compatible anchor URL for jump-to-source navigation."""
    if finding.evidence and finding.evidence.page_number is not None:
        page = finding.evidence.page_number
        return f"/api/documents/{doc_id}/view#page={page}&finding={finding.id}"
    return None


def build_highlight_map(
    document_id: str,
    findings: list[Finding],
) -> DocumentHighlightMap:
    """
    Build a complete DocumentHighlightMap from a list of findings.

    Each finding with an associated EvidenceSpan becomes a colored HighlightAnnotation.
    Findings without evidence still appear in the map (page_number=None) to allow
    the frontend to list them in the sidebar.
    """
    doc = doc_repository.get_document(document_id)
    filename = doc.filename if doc else document_id

    annotations: list[HighlightAnnotation] = []
    page_index: dict[str, list[str]] = {}

    for finding in findings:
        color = VERDICT_COLOR_MAP.get(str(finding.verdict), "#9E9E9E")
        label = f"{finding.rule_code}: {finding.verdict.upper()}"
        tooltip = _build_tooltip(finding)
        jump_url = _build_jump_url(document_id, finding)

        verbatim = None
        page_num = None
        char_start = None
        char_end = None

        if finding.evidence:
            verbatim = finding.evidence.verbatim_quote
            page_num = finding.evidence.page_number
            char_start = finding.evidence.char_start
            char_end = finding.evidence.char_end

        annotation = HighlightAnnotation(
            finding_id=finding.id,
            document_id=document_id,
            rule_code=finding.rule_code,
            rule_name=finding.rule_name,
            verdict=str(finding.verdict),
            severity=str(finding.severity),
            page_number=page_num,
            char_start=char_start,
            char_end=char_end,
            color=color,
            label=label,
            verbatim_quote=verbatim,
            jump_url=jump_url,
            tooltip_summary=tooltip,
        )
        annotations.append(annotation)

        # Build page index
        if page_num is not None:
            key = str(page_num)
            page_index.setdefault(key, []).append(finding.id)

    return DocumentHighlightMap(
        document_id=document_id,
        filename=filename,
        total_annotations=len(annotations),
        annotations=annotations,
        page_index=page_index,
    )
