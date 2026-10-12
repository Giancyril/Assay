import re

from pydantic import BaseModel


class EvidenceSpan(BaseModel):
    verbatim_quote: str
    page_number: int
    char_start: int
    char_end: int
    verified: bool = False
    rejection_reason: str | None = None


def normalize_whitespace(text: str) -> str:
    """Normalize repeated whitespace, tabs, and newlines to single spaces for fuzzy alignment."""
    return re.sub(r"\s+", " ", text).strip()


def verify_quote_in_page_text(
    verbatim_quote: str,
    page_text: str,
    page_number: int,
    char_offset_in_doc: int = 0
) -> tuple[bool, EvidenceSpan | None]:
    """
    Deterministically verify that verbatim_quote exists within page_text.
    Allows for whitespace differences while preserving exact character offsets.
    If the quote does not exist in the source text, the match fails and the finding is rejected.
    """
    if not verbatim_quote or not verbatim_quote.strip():
        return False, EvidenceSpan(
            verbatim_quote="",
            page_number=page_number,
            char_start=0,
            char_end=0,
            verified=False,
            rejection_reason="Empty or whitespace-only quote provided"
        )

    # 1. Direct exact substring match
    exact_idx = page_text.find(verbatim_quote)
    if exact_idx != -1:
        start = char_offset_in_doc + exact_idx
        end = start + len(verbatim_quote)
        return True, EvidenceSpan(
            verbatim_quote=verbatim_quote,
            page_number=page_number,
            char_start=start,
            char_end=end,
            verified=True
        )

    # 2. Whitespace-flexible regex match
    tokens = re.escape(verbatim_quote.strip()).split(r"\ ")
    pattern_str = r"\s+".join(tokens)
    try:
        match = re.search(pattern_str, page_text, re.IGNORECASE)
        if match:
            start = char_offset_in_doc + match.start()
            end = char_offset_in_doc + match.end()
            actual_text = page_text[match.start():match.end()]
            return True, EvidenceSpan(
                verbatim_quote=actual_text,
                page_number=page_number,
                char_start=start,
                char_end=end,
                verified=True
            )
    except Exception as e:
        return False, EvidenceSpan(
            verbatim_quote=verbatim_quote,
            page_number=page_number,
            char_start=0,
            char_end=0,
            verified=False,
            rejection_reason=f"Regex verification error: {e!s}"
        )

    # 3. Quote was not found in source text
    return False, EvidenceSpan(
        verbatim_quote=verbatim_quote,
        page_number=page_number,
        char_start=0,
        char_end=0,
        verified=False,
        rejection_reason="Verbatim quote not found in source document text (hallucination rejected)"
    )
