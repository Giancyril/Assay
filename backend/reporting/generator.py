from datetime import UTC, datetime

import pymupdf

from backend.agent.findings import Finding
from backend.ingestion.models import ParsedDocument
from backend.rules.models import Severity, Verdict


def generate_markdown_report(
    doc: ParsedDocument,
    findings: list[Finding],
    ruleset_name: str = "Commercial NDA Standard Policy",
    ruleset_version: str = "1.0.0",
) -> str:
    """Generates an executive-ready GitHub-flavored Markdown compliance audit report."""
    total = len(findings)
    violations = [f for f in findings if f.verdict == Verdict.VIOLATION or f.verdict == "violation"]
    needs_review = [f for f in findings if f.verdict == Verdict.NEEDS_REVIEW or f.verdict == "needs_review"]
    compliant = [f for f in findings if f.verdict == Verdict.COMPLIANT or f.verdict == "compliant"]

    score = round((len(compliant) / total * 100), 1) if total > 0 else 0.0

    if len(violations) > 0:
        overall_status = "**NON-COMPLIANT** (Critical violations detected)"
    elif len(needs_review) > 0:
        overall_status = "**REQUIRES HUMAN REVIEW** (Ambiguities detected)"
    else:
        overall_status = "**COMPLIANT** (All evaluated rules satisfied)"

    now_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = []
    md.append("# Contract Compliance Audit Report\n")
    md.append(f"> **Document:** `{doc.filename}`  \n")
    md.append(f"> **Audit Date:** {now_iso}  \n")
    md.append(f"> **Rule Set:** {ruleset_name} (v{ruleset_version})  \n")
    md.append(f"> **Overall Status:** {overall_status}  \n")
    md.append(f"> **Compliance Score:** {score}%\n")
    md.append("\n---\n")

    # Executive Summary Table
    md.append("## Executive Summary\n")
    md.append("| Outcome | Count | % of Rules | Action Required |")
    md.append("| :--- | :---: | :---: | :--- |")
    md.append(
        f"| **Violations** | {len(violations)} | {round(len(violations) / total * 100, 1) if total else 0}% | Immediate redline / strike required |"
    )
    md.append(
        f"| **Needs Review** | {len(needs_review)} | {round(len(needs_review) / total * 100, 1) if total else 0}% | Legal counsel / reviewer sign-off needed |"
    )
    md.append(
        f"| **Compliant** | {len(compliant)} | {round(len(compliant) / total * 100, 1) if total else 0}% | Accepted as drafted |"
    )
    md.append(f"| **Total Evaluated** | {total} | 100.0% | - |")
    md.append("\n---\n")

    # Severity Breakdown
    crit_count = sum(1 for f in violations if f.severity == Severity.CRITICAL or f.severity == "critical")
    high_count = sum(1 for f in violations if f.severity == Severity.HIGH or f.severity == "high")
    med_count = sum(
        1
        for f in findings
        if (f.severity == Severity.MEDIUM or f.severity == "medium")
        and f.verdict != Verdict.COMPLIANT
        and f.verdict != "compliant"
    )

    md.append("### Risk Breakdown\n")
    md.append(f"- **Critical Severity Violations:** {crit_count}")
    md.append(f"- **High Severity Violations:** {high_count}")
    md.append(f"- **Medium Severity Inconsistencies:** {med_count}")
    md.append("\n---\n")

    # Detailed Findings
    md.append("## Detailed Findings\n")

    # 1. Violations
    if violations:
        md.append("### Violations (Immediate Revision Required)\n")
        for f in violations:
            md.append(f"#### [{f.rule_code}] {f.rule_name}")
            md.append(
                f"- **Severity:** `{f.severity.upper() if isinstance(f.severity, str) else f.severity.value.upper()}` | **Confidence:** `{int(f.confidence * 100)}%`"
            )
            md.append(f"- **Reasoning:** {f.reasoning}")
            md.append(f"- **Recommended Action:** {f.recommended_action}")
            if f.evidence and f.evidence.verbatim_quote:
                verified_str = "Verified in Source" if f.evidence.verified else "UNVERIFIED"
                md.append("- **Verbatim Quote:**")
                md.append(f'  > "{f.evidence.verbatim_quote}"')
                md.append(
                    f"  *(Page {f.evidence.page_number}, Chars {f.evidence.char_start}–{f.evidence.char_end} | Evidence Status: {verified_str})*"
                )
            md.append("")

    # 2. Needs Review
    if needs_review:
        md.append("### Needs Human Review (Verification Required)\n")
        for f in needs_review:
            md.append(f"#### [{f.rule_code}] {f.rule_name}")
            md.append(
                f"- **Severity:** `{f.severity.upper() if isinstance(f.severity, str) else f.severity.value.upper()}` | **Confidence:** `{int(f.confidence * 100)}%`"
            )
            md.append(f"- **Reasoning:** {f.reasoning}")
            md.append(f"- **Recommended Action:** {f.recommended_action}")
            if f.evidence and f.evidence.verbatim_quote:
                md.append("- **Candidate Quote:**")
                md.append(f'  > "{f.evidence.verbatim_quote}"')
                md.append(f"  *(Page {f.evidence.page_number}, Chars {f.evidence.char_start}–{f.evidence.char_end})*")
            if f.searches_run:
                md.append(f"- **Absence Verification Searches:** `{', '.join(f.searches_run[:3])}`")
            md.append("")

    # 3. Compliant Findings
    if compliant:
        md.append("### Compliant Clauses\n")
        for f in compliant:
            md.append(f"- **[{f.rule_code}] {f.rule_name}**: {f.reasoning}")
            if f.evidence and f.evidence.verbatim_quote:
                md.append(f'  - *Quote (p. {f.evidence.page_number}):* "{f.evidence.verbatim_quote[:120]}..."')
        md.append("")

    # Audit Trail & Disclaimer
    md.append("\n---\n")
    md.append("## Audit Trail & Disclaimer\n")
    md.append("- **Verification Gate:** Deterministic String Span Matching (Exact & Normalized)")
    md.append(f"- **Model / Engine:** {findings[0].model_used if findings else 'Rules Engine v1.0'}")
    md.append("- **Document ID:** `" + doc.id + "`")
    md.append(
        "\n> **Legal Disclaimer:** This report is an automated compliance evaluation and issue organization aid intended for trained reviewers and legal counsel. It does not constitute legal advice or create an attorney-client relationship."
    )

    return "\n".join(md)


def generate_pdf_report(
    doc: ParsedDocument,
    findings: list[Finding],
    ruleset_name: str = "Commercial NDA Standard Policy",
    ruleset_version: str = "1.0.0",
) -> bytes:
    """Generates a publication-quality PDF audit report using PyMuPDF."""
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)  # Standard A4 size

    # Colors
    c_primary = (0.1, 0.15, 0.3)
    c_danger = (0.8, 0.15, 0.15)
    c_warning = (0.85, 0.55, 0.05)
    c_success = (0.1, 0.6, 0.25)
    c_gray = (0.35, 0.35, 0.35)

    y = 40.0

    # Header Title
    page.insert_text((40, y), "CONTRACT COMPLIANCE AUDIT REPORT", fontsize=15, fontname="helv", color=c_primary)
    y += 20
    page.draw_line((40, y), (555, y), color=c_primary, width=1.5)
    y += 18

    # Metadata Header Box
    now_iso = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    meta_text = (
        f"Document: {doc.filename}\n"
        f"Rule Set: {ruleset_name} (v{ruleset_version})\n"
        f"Audit Generated: {now_iso}\n"
        f"Document ID: {doc.id}"
    )
    page.insert_textbox(pymupdf.Rect(40, y, 555, y + 60), meta_text, fontsize=9, fontname="helv", color=c_gray)
    y += 65

    # Summary Metrics Badges
    total = len(findings)
    violations = [f for f in findings if f.verdict == Verdict.VIOLATION or f.verdict == "violation"]
    needs_review = [f for f in findings if f.verdict == Verdict.NEEDS_REVIEW or f.verdict == "needs_review"]
    compliant = [f for f in findings if f.verdict == Verdict.COMPLIANT or f.verdict == "compliant"]

    score = round((len(compliant) / total * 100), 1) if total > 0 else 0.0

    # Draw metric boxes
    box_w = 115
    boxes = [
        ("Score", f"{score}%", c_primary),
        ("Violations", str(len(violations)), c_danger if violations else c_success),
        ("Needs Review", str(len(needs_review)), c_warning if needs_review else c_gray),
        ("Compliant", str(len(compliant)), c_success),
    ]

    bx = 40.0
    for label, val, color in boxes:
        rect = pymupdf.Rect(bx, y, bx + box_w, y + 36)
        page.draw_rect(rect, color=color, fill=(0.96, 0.96, 0.97), width=1)
        page.insert_text((bx + 10, y + 15), label.upper(), fontsize=7, fontname="helv", color=c_gray)
        page.insert_text((bx + 10, y + 30), val, fontsize=12, fontname="helv", color=color)
        bx += box_w + 5

    y += 50

    # Section: Key Findings
    page.insert_text((40, y), "ACTIONABLE FINDINGS & EVIDENCE", fontsize=11, fontname="helv", color=c_primary)
    y += 10
    page.draw_line((40, y), (555, y), color=(0.8, 0.8, 0.8), width=0.5)
    y += 15

    critical_items = violations + needs_review

    for idx, f in enumerate(critical_items):
        if y > 750:
            page = pdf.new_page(width=595, height=842)
            y = 40.0

        is_violation = f.verdict == Verdict.VIOLATION or f.verdict == "violation"
        tag_color = c_danger if is_violation else c_warning
        verdict_label = "VIOLATION" if is_violation else "NEEDS REVIEW"

        card_rect = pymupdf.Rect(40, y, 555, y + 80)
        page.draw_rect(card_rect, color=(0.85, 0.85, 0.85), fill=(0.99, 0.99, 0.99), width=0.5)

        # Header of card
        page.insert_text((50, y + 16), f"[{f.rule_code}] {f.rule_name}", fontsize=9, fontname="helv", color=c_primary)
        page.insert_text((470, y + 16), verdict_label, fontsize=8, fontname="helv", color=tag_color)

        detail_lines = []
        detail_lines.append(f"Reason: {f.reasoning}")
        detail_lines.append(f"Action: {f.recommended_action}")
        if f.evidence and f.evidence.verbatim_quote:
            detail_lines.append(f'Quote (p.{f.evidence.page_number}): "{f.evidence.verbatim_quote[:140]}..."')

        text_block = "\n".join(detail_lines)
        page.insert_textbox(
            pymupdf.Rect(50, y + 22, 545, y + 78), text_block, fontsize=7.5, fontname="helv", color=(0.2, 0.2, 0.2)
        )

        y += 88

    # Compliant summary section
    if y > 730:
        page = pdf.new_page(width=595, height=842)
        y = 40.0

    page.insert_text((40, y), "COMPLIANT PROVISIONS", fontsize=10, fontname="helv", color=c_success)
    y += 10
    page.draw_line((40, y), (555, y), color=(0.8, 0.8, 0.8), width=0.5)
    y += 12

    for c in compliant:
        if y > 800:
            page = pdf.new_page(width=595, height=842)
            y = 40.0
        bullet = f"[PASS] {c.rule_code}: {c.rule_name} - {c.reasoning}"
        page.insert_textbox(
            pymupdf.Rect(45, y, 555, y + 18), bullet, fontsize=7.5, fontname="helv", color=(0.3, 0.3, 0.3)
        )
        y += 16

    # Footer Disclaimer
    disclaimer = (
        "CONFIDENTIAL & PRIVILEGED - AUTOMATED COMPLIANCE REVIEW AID\n"
        "This software does not provide legal advice or replace qualified legal counsel."
    )
    for p in pdf:
        p.insert_textbox(pymupdf.Rect(40, 810, 555, 835), disclaimer, fontsize=6.5, fontname="helv", color=c_gray)

    out_bytes = pdf.tobytes()
    pdf.close()
    return out_bytes
