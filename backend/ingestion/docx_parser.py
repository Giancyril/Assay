import io
import re
import uuid
from typing import List, Optional
import docx
from backend.ingestion.models import ParsedDocument, DocumentPage, TextSpan, DocumentFileType


def parse_docx(
    file_bytes: bytes,
    filename: str,
    doc_id: Optional[str] = None,
    storage_path: str = ""
) -> ParsedDocument:
    """
    Parses a DOCX document, extracting headings, paragraphs, and tables,
    mapping text to synthetic pages and calculating character offsets.
    """
    doc_id = doc_id or f"doc-{uuid.uuid4().hex[:12]}"
    doc = docx.Document(io.BytesIO(file_bytes))
    
    extracted_elements: List[dict] = []

    # 1. Extract paragraphs
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        style_name = p.style.name if p.style else "Normal"
        block_type = "heading" if "Heading" in style_name or re.match(r"^(SECTION|ARTICLE|\d+(\.\d+)*)\b", text, re.IGNORECASE) else "paragraph"
        extracted_elements.append({
            "text": text,
            "block_type": block_type,
            "style": style_name
        })

    # 2. Extract tables
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            cell_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cell_texts:
                combined_row = " | ".join(cell_texts)
                extracted_elements.append({
                    "text": combined_row,
                    "block_type": "table_cell",
                    "style": f"Table-{table_idx}-Row-{row_idx}"
                })

    # Divide into synthetic pages (approx 2,500 characters per page or explicit page boundaries)
    PAGE_CHAR_BUDGET = 2500
    pages: List[DocumentPage] = []
    full_text_parts: List[str] = []
    
    current_doc_offset = 0
    current_page_num = 1
    current_page_spans: List[TextSpan] = []
    current_page_pieces: List[str] = []
    current_page_offset = 0

    for elem in extracted_elements:
        text = elem["text"]
        # If adding text exceeds budget and page has text, close current page
        if current_page_offset + len(text) > PAGE_CHAR_BUDGET and current_page_pieces:
            page_text = "\n\n".join(current_page_pieces)
            page_start = current_doc_offset
            page_end = current_doc_offset + len(page_text)
            pages.append(
                DocumentPage(
                    page_number=current_page_num,
                    text=page_text,
                    char_start_doc=page_start,
                    char_end_doc=page_end,
                    is_ocr=False,
                    spans=current_page_spans,
                    metadata={"synthetic_page": True}
                )
            )
            full_text_parts.append(page_text)
            current_doc_offset += len(page_text) + 2
            current_page_num += 1
            current_page_spans = []
            current_page_pieces = []
            current_page_offset = 0

        span_start_page = current_page_offset
        span_end_page = span_start_page + len(text)
        span_start_doc = current_doc_offset + span_start_page
        span_end_doc = current_doc_offset + span_end_page

        current_page_spans.append(
            TextSpan(
                page_number=current_page_num,
                char_start_page=span_start_page,
                char_end_page=span_end_page,
                char_start_doc=span_start_doc,
                char_end_doc=span_end_doc,
                text=text,
                block_type=elem["block_type"]
            )
        )
        current_page_pieces.append(text)
        current_page_offset += len(text) + 2

    # Flush final page
    if current_page_pieces:
        page_text = "\n\n".join(current_page_pieces)
        page_start = current_doc_offset
        page_end = current_doc_offset + len(page_text)
        pages.append(
            DocumentPage(
                page_number=current_page_num,
                text=page_text,
                char_start_doc=page_start,
                char_end_doc=page_end,
                is_ocr=False,
                spans=current_page_spans,
                metadata={"synthetic_page": True}
            )
        )
        full_text_parts.append(page_text)

    full_document_text = "\n\n".join(full_text_parts)

    return ParsedDocument(
        id=doc_id,
        filename=filename,
        file_type=DocumentFileType.DOCX,
        file_size_bytes=len(file_bytes),
        storage_path=storage_path,
        full_text=full_document_text,
        page_count=len(pages),
        is_ocr=False,
        pages=pages,
        metadata={
            "paragraph_count": len(doc.paragraphs),
            "table_count": len(doc.tables),
            "format": "DOCX"
        }
    )
