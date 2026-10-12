import re
import uuid
from typing import List, Optional, Tuple
from backend.ingestion.models import ParsedDocument
from backend.indexing.models import ClauseChunk

# Regex patterns for detecting contract sections and headings
HEADING_PATTERNS = [
    # "1. DEFINITIONS", "1.1 Confidential Information", "12.3 Limitation of Liability"
    re.compile(r"^(\d+(\.\d+)*)\.?\s+([A-Za-z0-9\s\-_,;:()/'\"]{3,50})", re.MULTILINE),
    # "SECTION 1 - GOVERNING LAW", "ARTICLE IV: CONFIDENTIALITY", "CLAUSE 3.2"
    re.compile(r"^(SECTION|ARTICLE|CLAUSE)\s+([IVXLCDM\d]+(\.\d+)*)[:.\-\s]+([A-Za-z0-9\s\-_,;:()/'\"]{3,50})", re.IGNORECASE | re.MULTILINE),
    # Standalone UPPERCASE heading line, e.g. "MUTUAL NON-DISCLOSURE AGREEMENT"
    re.compile(r"^([A-Z0-9\s\-_,;:()/'\"]{5,60})$", re.MULTILINE),
]


def extract_section_headers(text: str) -> List[Tuple[int, int, Optional[str], str]]:
    """
    Finds section boundaries in text.
    Returns list of (start_char, end_char, section_number, section_title).
    """
    headers = []
    lines = text.split("\n")
    char_offset = 0

    for line in lines:
        line_stripped = line.strip()
        line_len = len(line)
        if 3 <= len(line_stripped) <= 80:
            matched = False
            # Check pattern 1: "1. DEFINITIONS"
            m1 = re.match(r"^(\d+(\.\d+)*)\.?\s+(.+)$", line_stripped)
            if m1:
                sec_num = m1.group(1)
                sec_title = m1.group(3).strip()
                headers.append((char_offset, char_offset + line_len, sec_num, sec_title))
                matched = True

            # Check pattern 2: "SECTION 1: TERM"
            if not matched:
                m2 = re.match(r"^(SECTION|ARTICLE|CLAUSE)\s+([IVXLCDM\d]+(\.\d+)*)[:.\-\s]+(.+)$", line_stripped, re.IGNORECASE)
                if m2:
                    sec_num = f"{m2.group(1).upper()} {m2.group(2)}"
                    sec_title = m2.group(4).strip()
                    headers.append((char_offset, char_offset + line_len, sec_num, sec_title))
                    matched = True

            # Check pattern 3: Short all-caps heading
            if not matched and line_stripped.isupper() and len(line_stripped.split()) <= 6:
                headers.append((char_offset, char_offset + line_len, None, line_stripped))
                matched = True

        char_offset += line_len + 1  # newline

    return headers


def find_page_for_offset(parsed_doc: ParsedDocument, offset: int) -> int:
    """Finds the 1-indexed page number containing a given document character offset."""
    for page in parsed_doc.pages:
        if page.char_start_doc <= offset <= page.char_end_doc:
            return page.page_number
    return 1 if not parsed_doc.pages else parsed_doc.pages[-1].page_number


def chunk_document_by_structure(parsed_doc: ParsedDocument) -> List[ClauseChunk]:
    """
    Splits a document into structure-aware clause chunks.
    Ensures clauses are not split mid-sentence or mid-section, keeping section
    number, title, exact character offsets, and page numbers intact.
    """
    text = parsed_doc.full_text
    if not text.strip():
        return []

    headers = extract_section_headers(text)
    chunks: List[ClauseChunk] = []

    # If no headers detected, chunk into clean paragraph-based segments
    if not headers:
        paragraphs = text.split("\n\n")
        offset = 0
        for i, para in enumerate(paragraphs):
            para_clean = para.strip()
            if not para_clean:
                offset += len(para) + 2
                continue
            p_start = offset + text[offset:].find(para_clean)
            p_end = p_start + len(para_clean)
            page_num = find_page_for_offset(parsed_doc, p_start)
            chunks.append(
                ClauseChunk(
                    id=f"{parsed_doc.id}-chunk-{i+1}",
                    document_id=parsed_doc.id,
                    section_number=None,
                    section_title=f"Paragraph {i+1}",
                    content=para_clean,
                    page_start=page_num,
                    page_end=find_page_for_offset(parsed_doc, p_end),
                    char_start_doc=p_start,
                    char_end_doc=p_end
                )
            )
            offset += len(para) + 2
        return chunks

    # Handle preamble before first header if present
    first_header_start = headers[0][0]
    if first_header_start > 50:
        preamble_text = text[:first_header_start].strip()
        if preamble_text:
            chunks.append(
                ClauseChunk(
                    id=f"{parsed_doc.id}-preamble",
                    document_id=parsed_doc.id,
                    section_number="0",
                    section_title="Preamble / Recitals",
                    content=preamble_text,
                    page_start=1,
                    page_end=find_page_for_offset(parsed_doc, len(preamble_text)),
                    char_start_doc=0,
                    char_end_doc=len(preamble_text)
                )
            )

    # Process each section between headers
    for i, (h_start, h_end, sec_num, sec_title) in enumerate(headers):
        # Section text extends until the next header, or end of document
        if i + 1 < len(headers):
            sec_end = headers[i + 1][0]
        else:
            sec_end = len(text)

        section_raw = text[h_start:sec_end].strip()
        if not section_raw:
            continue

        actual_start = text.find(section_raw, h_start)
        actual_end = actual_start + len(section_raw)

        # If a single section is very large (> 2500 chars), split into sub-clauses
        if len(section_raw) > 2500:
            paragraphs = section_raw.split("\n\n")
            sub_offset = actual_start
            for sub_idx, sub_p in enumerate(paragraphs):
                sub_clean = sub_p.strip()
                if not sub_clean:
                    sub_offset += len(sub_p) + 2
                    continue
                p_start = text.find(sub_clean, sub_offset)
                p_end = p_start + len(sub_clean)
                chunks.append(
                    ClauseChunk(
                        id=f"{parsed_doc.id}-clause-{i+1}-{sub_idx+1}",
                        document_id=parsed_doc.id,
                        section_number=sec_num,
                        section_title=f"{sec_title} (Part {sub_idx+1})",
                        content=sub_clean,
                        page_start=find_page_for_offset(parsed_doc, p_start),
                        page_end=find_page_for_offset(parsed_doc, p_end),
                        char_start_doc=p_start,
                        char_end_doc=p_end
                    )
                )
                sub_offset = p_end
        else:
            chunks.append(
                ClauseChunk(
                    id=f"{parsed_doc.id}-clause-{i+1}",
                    document_id=parsed_doc.id,
                    section_number=sec_num,
                    section_title=sec_title,
                    content=section_raw,
                    page_start=find_page_for_offset(parsed_doc, actual_start),
                    page_end=find_page_for_offset(parsed_doc, actual_end),
                    char_start_doc=actual_start,
                    char_end_doc=actual_end
                )
            )

    return chunks
