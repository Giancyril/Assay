import re
import uuid

from backend.compare.models import (
    ClauseComparisonItem,
    ComparativeAuditResult,
    ConflictSeverity,
    ConflictType,
    DocumentConflict,
)
from backend.ingestion.models import ParsedDocument

JURISDICTION_PATTERNS = [
    (
        r"(?i)(?:governed by|laws of|jurisdiction of)\s+(?:the\s+state\s+of\s+)?([A-Za-z\s]+?)(?:\.|,|\s+without|\s+and|\s*;\s*)",
        1,
    ),
    (r"(?i)state of\s+([A-Za-z]+)", 1),
    (r"(?i)(Delaware|New York|California|Texas|England and Wales|Singapore|Washington)", 1),
]

DURATION_PATTERNS = [
    (r"(?i)(\d+)\s*(?:years?|yrs?)", "years"),
    (r"(?i)(\d+)\s*(?:months?|mos?)", "months"),
    (r"(?i)(perpetual|indefinite|survive indefinitely)", "perpetual"),
]

NOTICE_PATTERNS = [
    (r"(?i)(\d+)\s*(?:days?|calendar days?|business days?)\s*(?:written\s+)?notice", 1),
    (r"(?i)notice of\s*(\d+)\s*days", 1),
]


def _extract_jurisdiction(text: str) -> str | None:
    for pat, grp in JURISDICTION_PATTERNS:
        m = re.search(pat, text)
        if m:
            val = m.group(grp).strip()
            if 2 < len(val) < 40:
                return val.title()
    return None


def _extract_duration(text: str) -> str | None:
    for pat, unit in DURATION_PATTERNS:
        m = re.search(pat, text)
        if m:
            if unit == "perpetual":
                return "Perpetual"
            return f"{m.group(1)} {unit}"
    return None


def _extract_notice_period(text: str) -> int | None:
    for pat, grp in NOTICE_PATTERNS:
        m = re.search(pat, text)
        if m:
            try:
                return int(m.group(grp))
            except ValueError:
                continue
    return None


class ComparativeConflictEngine:
    """Compares two contract documents and identifies conflicting clauses and risk misalignments."""

    @classmethod
    def compare(
        cls,
        doc_a: ParsedDocument,
        doc_b: ParsedDocument,
        doc_a_role: str = "Primary Agreement",
        doc_b_role: str = "Secondary / Addendum",
    ) -> ComparativeAuditResult:
        conflicts: list[DocumentConflict] = []
        clause_items: list[ClauseComparisonItem] = []
        text_a = doc_a.full_text
        text_b = doc_b.full_text

        # 1. Governing Law Check
        jur_a = _extract_jurisdiction(text_a)
        jur_b = _extract_jurisdiction(text_b)
        has_jur_conflict = bool(jur_a and jur_b and jur_a.lower() != jur_b.lower())

        jur_item = ClauseComparisonItem(
            category="Governing Law & Jurisdiction",
            doc_a_extracted_value=jur_a or "Unspecified",
            doc_b_extracted_value=jur_b or "Unspecified",
            has_conflict=has_jur_conflict,
            conflict_type=ConflictType.GOVERNING_LAW_MISMATCH if has_jur_conflict else None,
            severity=ConflictSeverity.CRITICAL if has_jur_conflict else None,
            explanation=(
                f"{doc_a_role} stipulates {jur_a} law whereas {doc_b_role} designates {jur_b}."
                if has_jur_conflict
                else "Both documents are aligned or jurisdiction is single-sourced."
            ),
            recommended_resolution=(
                f"Harmonize governing law to {jur_a} or explicitly establish precedence clause in {doc_a_role}."
                if has_jur_conflict
                else None
            ),
        )
        clause_items.append(jur_item)
        if has_jur_conflict:
            conflicts.append(
                DocumentConflict(
                    id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.GOVERNING_LAW_MISMATCH,
                    severity=ConflictSeverity.CRITICAL,
                    topic="Governing Law Contradiction",
                    doc_a_excerpt=f"Governing law: {jur_a}",
                    doc_b_excerpt=f"Governing law: {jur_b}",
                    explanation=f"{doc_a_role} selects {jur_a} while {doc_b_role} selects {jur_b}. This creates legal dispute risks.",
                    remediation_suggestion=f"Add: 'In the event of conflict, the governing law specified in {doc_a_role} ({jur_a}) shall govern.'",
                )
            )

        # 2. Duration / Term Check
        dur_a = _extract_duration(text_a)
        dur_b = _extract_duration(text_b)
        has_dur_conflict = bool(dur_a and dur_b and dur_a.lower() != dur_b.lower())

        dur_item = ClauseComparisonItem(
            category="Term & Confidentiality Duration",
            doc_a_extracted_value=dur_a or "Unspecified",
            doc_b_extracted_value=dur_b or "Unspecified",
            has_conflict=has_dur_conflict,
            conflict_type=ConflictType.DURATION_MISMATCH if has_dur_conflict else None,
            severity=ConflictSeverity.HIGH if has_dur_conflict else None,
            explanation=(
                f"{doc_a_role} sets confidentiality duration to {dur_a}, whereas {doc_b_role} sets {dur_b}."
                if has_dur_conflict
                else "Durations are consistent across both agreements."
            ),
            recommended_resolution=(
                "Standardize the survival term across both documents to avoid lingering perpetual obligations."
                if has_dur_conflict
                else None
            ),
        )
        clause_items.append(dur_item)
        if has_dur_conflict:
            conflicts.append(
                DocumentConflict(
                    id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.DURATION_MISMATCH,
                    severity=ConflictSeverity.HIGH,
                    topic="Confidentiality Duration Mismatch",
                    doc_a_excerpt=f"Confidentiality term: {dur_a}",
                    doc_b_excerpt=f"Confidentiality term: {dur_b}",
                    explanation=f"Contradictory duration periods ({dur_a} vs {dur_b}) lead to uncertain obligation horizons.",
                    remediation_suggestion="Adopt the commercially standard 3 or 5-year duration across both agreements.",
                )
            )

        # 3. Termination Notice Period Check
        not_a = _extract_notice_period(text_a)
        not_b = _extract_notice_period(text_b)
        has_not_conflict = bool(not_a and not_b and not_a != not_b)

        not_item = ClauseComparisonItem(
            category="Termination Notice Period",
            doc_a_extracted_value=f"{not_a} days" if not_a else "Unspecified",
            doc_b_extracted_value=f"{not_b} days" if not_b else "Unspecified",
            has_conflict=has_not_conflict,
            conflict_type=ConflictType.NOTICE_PERIOD_MISMATCH if has_not_conflict else None,
            severity=ConflictSeverity.MEDIUM if has_not_conflict else None,
            explanation=(
                f"{doc_a_role} requires {not_a} days notice whereas {doc_b_role} requires {not_b} days."
                if has_not_conflict
                else "Termination notice provisions are aligned."
            ),
            recommended_resolution=(
                f"Harmonize notice period to {min(not_a or 30, not_b or 30)} days." if has_not_conflict else None
            ),
        )
        clause_items.append(not_item)
        if has_not_conflict:
            conflicts.append(
                DocumentConflict(
                    id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.NOTICE_PERIOD_MISMATCH,
                    severity=ConflictSeverity.MEDIUM,
                    topic="Notice Period Discrepancy",
                    doc_a_excerpt=f"{not_a} days notice",
                    doc_b_excerpt=f"{not_b} days notice",
                    explanation=f"Asymmetrical notice periods ({not_a} vs {not_b} days) create procedural breach risks.",
                    remediation_suggestion="Align notice requirements to a single timeframe across all exhibits.",
                )
            )

        # 4. Confidentiality Marking Requirement Check
        marking_a = bool(re.search(r"(?i)(?:marked|labeled)\s+confidential", text_a))
        marking_b = bool(re.search(r"(?i)(?:marked|labeled)\s+confidential", text_b))
        has_mark_conflict = marking_a != marking_b

        mark_item = ClauseComparisonItem(
            category="Confidentiality Marking Requirement",
            doc_a_extracted_value="Marking Required" if marking_a else "Automatic Protection",
            doc_b_extracted_value="Marking Required" if marking_b else "Automatic Protection",
            has_conflict=has_mark_conflict,
            conflict_type=ConflictType.CONFIDENTIALITY_SCOPE_MISMATCH if has_mark_conflict else None,
            severity=ConflictSeverity.HIGH if has_mark_conflict else None,
            explanation=(
                "One agreement requires written confidentiality markings while the other grants automatic protection."
                if has_mark_conflict
                else "Marking standards are aligned."
            ),
            recommended_resolution=(
                "Clarify whether unmarked oral or visual disclosures qualify for protection."
                if has_mark_conflict
                else None
            ),
        )
        clause_items.append(mark_item)
        if has_mark_conflict:
            conflicts.append(
                DocumentConflict(
                    id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.CONFIDENTIALITY_SCOPE_MISMATCH,
                    severity=ConflictSeverity.HIGH,
                    topic="Confidentiality Definition Inconsistency",
                    doc_a_excerpt="Marked confidential" if marking_a else "Automatic protection",
                    doc_b_excerpt="Marked confidential" if marking_b else "Automatic protection",
                    explanation="Discrepancy in marking clauses risks accidental waiver of confidential protection.",
                    remediation_suggestion="Use comprehensive standard definition: 'Disclosed information reasonably understood to be confidential'.",
                )
            )

        # Calculate Alignment Score
        crit_count = sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)
        high_count = sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)
        med_count = sum(1 for c in conflicts if c.severity == ConflictSeverity.MEDIUM)

        penalty = (crit_count * 25.0) + (high_count * 15.0) + (med_count * 10.0)
        alignment_score = max(0.0, min(100.0, 100.0 - penalty))

        return ComparativeAuditResult(
            comparison_id=f"compare-{uuid.uuid4().hex[:8]}",
            doc_a_id=doc_a.id,
            doc_b_id=doc_b.id,
            doc_a_filename=doc_a.filename,
            doc_b_filename=doc_b.filename,
            total_conflicts=len(conflicts),
            critical_conflicts=crit_count,
            high_conflicts=high_count,
            alignment_score=round(alignment_score, 1),
            conflicts=conflicts,
            clause_comparisons=clause_items,
        )
