import re

from backend.rules.models import ComplianceRule, PrecheckResult, RuleType, Verdict


def extract_surrounding_sentence(text: str, match_start: int, match_end: int) -> str:
    """Extracts the complete sentence surrounding a regex match for verbatim evidence."""
    # Find sentence start (period, newline, or text start)
    start = max(0, text.rfind("\n", 0, match_start) + 1)
    period_start = text.rfind(". ", 0, match_start)
    if period_start != -1 and period_start + 2 > start:
        start = period_start + 2

    # Find sentence end
    end = text.find("\n", match_end)
    period_end = text.find(". ", match_end)
    if period_end != -1 and (end == -1 or period_end < end):
        end = period_end + 1
    elif end == -1:
        end = len(text)

    sentence = text[start:end].strip()
    return sentence if sentence else text[match_start:match_end]


def check_prohibited_terms(text: str, rule: ComplianceRule) -> PrecheckResult | None:
    """Deterministically checks for prohibited contract terms using regex patterns."""
    regex_pattern = rule.deterministic_regex
    if not regex_pattern and rule.parameters.prohibited_terms:
        escaped_terms = [re.escape(t) for t in rule.parameters.prohibited_terms]
        regex_pattern = r"\b(" + "|".join(escaped_terms) + r")\b"

    if not regex_pattern:
        return None

    match = re.search(regex_pattern, text, re.IGNORECASE)
    if match:
        quote = extract_surrounding_sentence(text, match.start(), match.end())
        matched_word = match.group(0)
        return PrecheckResult(
            has_deterministic_verdict=True,
            verdict=Verdict.VIOLATION,
            evidence_quote=quote,
            matched_term=matched_word,
            confidence=1.0,
            reasoning=f"Prohibited term '{matched_word}' detected matching rule {rule.code} ({rule.name}).",
        )
    return None


def check_numeric_duration_threshold(text: str, rule: ComplianceRule) -> PrecheckResult | None:
    """Deterministically checks confidentiality term duration vs maximum permissible threshold."""
    # 1. Check perpetual duration
    perpetual_match = re.search(
        r"\b(in perpetuity|indefinite(ly)?|survive forever|without limitation in time)\b", text, re.IGNORECASE
    )
    if perpetual_match:
        if rule.parameters.allow_perpetual is False:
            quote = extract_surrounding_sentence(text, perpetual_match.start(), perpetual_match.end())
            return PrecheckResult(
                has_deterministic_verdict=True,
                verdict=Verdict.VIOLATION,
                evidence_quote=quote,
                matched_term=perpetual_match.group(0),
                confidence=1.0,
                reasoning=f"Clause imposes perpetual/indefinite duration ({perpetual_match.group(0)}), which violates policy cap.",
            )

    # 2. Extract numeric duration (e.g., 'three (3) years', '5 years', '36 months')
    num_match = re.search(
        r"\b(?:expire|last|term|remain in effect|period of)\s+(?:for\s+)?(?:[a-zA-Z]+\s+\()?(\d+)\)?\s+(years?|months?)\b",
        text,
        re.IGNORECASE,
    )
    if not num_match:
        num_match = re.search(
            r"\b(?:[a-zA-Z]+\s+\()?(\d+)\)?\s+(years?|months?)\s+(?:from|following|after|of)\b", text, re.IGNORECASE
        )

    if num_match and rule.parameters.max_threshold is not None:
        val = int(num_match.group(1))
        unit = num_match.group(2).lower()
        # Convert to months if rule threshold is in months
        months = val * 12 if "year" in unit else val
        max_months = rule.parameters.max_threshold

        quote = extract_surrounding_sentence(text, num_match.start(), num_match.end())

        if months > max_months:
            return PrecheckResult(
                has_deterministic_verdict=True,
                verdict=Verdict.VIOLATION,
                evidence_quote=quote,
                matched_term=num_match.group(0),
                confidence=0.98,
                reasoning=f"Confidentiality duration of {val} {unit} ({months} months) exceeds maximum allowed threshold of {max_months} months.",
            )
        else:
            return PrecheckResult(
                has_deterministic_verdict=True,
                verdict=Verdict.COMPLIANT,
                evidence_quote=quote,
                matched_term=num_match.group(0),
                confidence=0.95,
                reasoning=f"Confidentiality duration of {val} {unit} ({months} months) is within acceptable threshold of {max_months} months.",
            )

    return None


def check_numeric_notice_threshold(text: str, rule: ComplianceRule) -> PrecheckResult | None:
    """Deterministically checks notice period (e.g. min 30 days notice for termination)."""
    notice_match = re.search(
        r"\b(?:[a-zA-Z]+\s+\()?(\d+)\)?\s+days?(?:['\u2019])?\s*(?:prior\s+)?(?:written\s+)?notice\b",
        text,
        re.IGNORECASE,
    )
    if notice_match and rule.parameters.min_threshold is not None:
        days = int(notice_match.group(1))
        min_days = int(rule.parameters.min_threshold)
        quote = extract_surrounding_sentence(text, notice_match.start(), notice_match.end())

        if days < min_days:
            return PrecheckResult(
                has_deterministic_verdict=True,
                verdict=Verdict.VIOLATION,
                evidence_quote=quote,
                matched_term=notice_match.group(0),
                confidence=0.98,
                reasoning=f"Notice period of {days} days is below required minimum threshold of {min_days} days.",
            )
        else:
            return PrecheckResult(
                has_deterministic_verdict=True,
                verdict=Verdict.COMPLIANT,
                evidence_quote=quote,
                matched_term=notice_match.group(0),
                confidence=0.95,
                reasoning=f"Notice period of {days} days meets required minimum threshold of {min_days} days.",
            )

    return None


def run_deterministic_precheck(candidate_text: str, rule: ComplianceRule) -> PrecheckResult:
    """
    Executes all applicable deterministic pre-checks against candidate text.
    If a deterministic match is found, returns high-confidence verdict without LLM call.
    """
    if not candidate_text or not candidate_text.strip():
        return PrecheckResult(has_deterministic_verdict=False)

    # 1. Prohibited terms
    if rule.rule_type == RuleType.PROHIBITED_TERM or rule.deterministic_regex:
        res = check_prohibited_terms(candidate_text, rule)
        if res:
            return res

    # 2. Numeric threshold (duration / notice)
    if rule.rule_type == RuleType.NUMERIC_THRESHOLD:
        if rule.parameters.unit == "months" or rule.parameters.allow_perpetual is not None:
            res = check_numeric_duration_threshold(candidate_text, rule)
            if res:
                return res
        if rule.parameters.unit == "days" or rule.parameters.min_threshold is not None:
            res = check_numeric_notice_threshold(candidate_text, rule)
            if res:
                return res

    return PrecheckResult(has_deterministic_verdict=False)
