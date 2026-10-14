import difflib
import re

from backend.agent.findings import Finding
from backend.redline.models import DiffOp, DiffToken, RedlineDiff
from backend.rules.models import ComplianceRule, Verdict


def compute_word_diff(original: str, remediated: str) -> tuple[list[DiffToken], str, str]:
    """
    Computes fine-grained word-level diff tokens, inline markup ([-old-]{+new+}),
    and a unified diff string between original and remediated clause text.
    """
    # Tokenize preserving whitespace and punctuation
    orig_words = re.findall(r"\S+|\s+", original)
    rem_words = re.findall(r"\S+|\s+", remediated)

    matcher = difflib.SequenceMatcher(None, orig_words, rem_words)
    tokens: list[DiffToken] = []
    inline_parts: list[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            chunk = "".join(orig_words[i1:i2])
            tokens.append(DiffToken(op=DiffOp.EQUAL, text=chunk))
            inline_parts.append(chunk)
        elif tag == "delete":
            chunk = "".join(orig_words[i1:i2])
            tokens.append(DiffToken(op=DiffOp.DELETE, text=chunk))
            inline_parts.append(f"[-{chunk}-]")
        elif tag == "insert":
            chunk = "".join(rem_words[j1:j2])
            tokens.append(DiffToken(op=DiffOp.INSERT, text=chunk))
            inline_parts.append(f"{{+{chunk}+}}")
        elif tag == "replace":
            del_chunk = "".join(orig_words[i1:i2])
            ins_chunk = "".join(rem_words[j1:j2])
            tokens.append(DiffToken(op=DiffOp.DELETE, text=del_chunk))
            tokens.append(DiffToken(op=DiffOp.INSERT, text=ins_chunk))
            inline_parts.append(f"[-{del_chunk}-]{{+{ins_chunk}+}}")

    inline_markup = "".join(inline_parts)

    unified = "\n".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            remediated.splitlines(keepends=True),
            fromfile="original_clause",
            tofile="remediated_clause",
            lineterm="",
        )
    )

    return tokens, inline_markup, unified


class RedlineEngine:
    """
    Authoritative automated contract redlining engine.
    Generates standardized compliant replacement clauses that resolve violations
    while preserving non-offending contractual terms.
    """

    @staticmethod
    def generate_remediation_clause(finding: Finding, rule: ComplianceRule | None = None) -> tuple[str, str]:
        """
        Returns (remediated_clause_text, legal_rationale) tailored to the specific rule violation.
        """
        code = finding.rule_code
        quote = finding.evidence.verbatim_quote if finding.evidence else ""

        # NDA-02: Confidentiality Term Limit (e.g. perpetual / indefinite)
        if code == "NDA-02":
            if quote and re.search(r"\b(in perpetuity|indefinite(ly)?|survive forever)\b", quote, re.IGNORECASE):
                remediated = re.sub(
                    r"\b(in perpetuity|indefinite(ly)?|survive forever|without limitation in time)\b",
                    "for a period of three (3) years from the Effective Date of this Agreement",
                    quote,
                    flags=re.IGNORECASE,
                )
            elif quote:
                remediated = f"{quote.rstrip('.')} (provided that in no event shall confidentiality obligations exceed three (3) years from the date of disclosure)."
            else:
                remediated = "The confidentiality obligations set forth herein shall survive termination of this Agreement and continue for a period of three (3) years from the Effective Date."

            rationale = "Replaced indefinite/perpetual term with standard 3-year commercial cap complying with NDA-02 policy limit."
            return remediated, rationale

        # NDA-05: Non-Solicitation Encroachment (Strict Prohibition)
        if code == "NDA-05":
            remediated = "[Intentionally Deleted - Non-solicitation restrictions are omitted in accordance with preliminary NDA policy]."
            rationale = (
                "Non-solicitation restrictions must be struck entirely from preliminary confidentiality agreements."
            )
            return remediated, rationale

        # NDA-04: Approved Governing Law & Forum
        if code == "NDA-04":
            if quote:
                remediated = re.sub(
                    r"\b(laws of the [A-Za-z\s]+|laws of [A-Za-z\s]+)\b",
                    "laws of the State of Delaware",
                    quote,
                    flags=re.IGNORECASE,
                )
            else:
                remediated = "This Agreement shall be governed by, and construed in accordance with, the laws of the State of Delaware, without giving effect to conflicts of law principles."
            rationale = "Amended governing law to designated approved jurisdiction (State of Delaware) in compliance with NDA-04."
            return remediated, rationale

        # NDA-03: Return or Destruction of Materials
        if code == "NDA-03":
            if quote:
                remediated = (
                    quote.rstrip(".")
                    + "; provided that Recipient may retain archival copies of Confidential Information solely for routine IT backup and regulatory compliance purposes."
                )
            else:
                remediated = "Upon written request, Recipient shall promptly return or certify destruction of all Confidential Information, provided that automated archival IT backups may be retained subject to continued confidentiality."
            rationale = "Added mandatory archival IT backup retention carve-out complying with NDA-03."
            return remediated, rationale

        # NDA-01: Exclusions & Carve-outs
        if code == "NDA-01":
            remediated = (
                "Confidential Information shall not include information that: (a) is or becomes publicly known through no breach by Recipient; "
                "(b) was already in Recipient's possession prior to disclosure; (c) is independently developed by Recipient without access to Discloser's information; "
                "or (d) is required to be disclosed pursuant to a valid court order or subpoena."
            )
            rationale = "Restored full 4-part standard carve-outs (public domain, prior receipt, independent development, legal compulsion)."
            return remediated, rationale

        # General / Custom fallback
        if finding.recommended_action:
            remediated = f"/* Redline recommendation: {finding.recommended_action} */\n{quote}"
            rationale = finding.recommended_action
        else:
            remediated = f"[Amended to satisfy compliance rule {code} ({finding.rule_name})]"
            rationale = finding.reasoning

        return remediated, rationale

    def generate_redline_for_finding(self, finding: Finding, rule: ComplianceRule | None = None) -> RedlineDiff:
        """
        Creates a structured RedlineDiff with word-level tokens, unified diff,
        and inline markup for an individual finding.
        """
        original = (
            finding.evidence.verbatim_quote
            if finding.evidence and finding.evidence.verbatim_quote
            else finding.reasoning
        )
        remediated, rationale = self.generate_remediation_clause(finding, rule)

        tokens, inline_markup, unified = compute_word_diff(original, remediated)

        return RedlineDiff(
            finding_id=finding.id,
            rule_code=finding.rule_code,
            rule_name=finding.rule_name,
            original_text=original,
            remediated_text=remediated,
            inline_markup=inline_markup,
            unified_diff=unified,
            tokens=tokens,
            legal_rationale=rationale,
            page_number=finding.evidence.page_number if finding.evidence else None,
            char_start=finding.evidence.char_start if finding.evidence else None,
            char_end=finding.evidence.char_end if finding.evidence else None,
        )

    def generate_all_redlines(self, findings: list[Finding]) -> list[RedlineDiff]:
        """
        Generates redline diffs for all findings requiring revision (violations and needs_review).
        """
        actionable = [
            f for f in findings if f.verdict in (Verdict.VIOLATION, Verdict.NEEDS_REVIEW, "violation", "needs_review")
        ]
        return [self.generate_redline_for_finding(f) for f in actionable]


redline_engine = RedlineEngine()
