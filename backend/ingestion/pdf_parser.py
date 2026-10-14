import re
import uuid

import pymupdf

from backend.ingestion.models import (
    DocumentFileType,
    DocumentPage,
    ParsedDocument,
    TextSpan,
)


def parse_pdf(file_bytes: bytes, filename: str, doc_id: str | None = None, storage_path: str = "") -> ParsedDocument:
    """
    Parses a PDF document, preserving exact page numbers, character offsets,
    and identifying scanned pages requiring OCR fallback.
    """
    doc_id = doc_id or f"doc-{uuid.uuid4().hex[:12]}"
    pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")

    pages: list[DocumentPage] = []
    full_text_parts: list[str] = []
    current_doc_offset = 0
    document_is_ocr = False

    for page_index in range(len(pdf_doc)):
        page = pdf_doc[page_index]
        page_number = page_index + 1

        # Extract text blocks: tuple (x0, y0, x1, y1, text, block_no, block_type)
        raw_blocks = page.get_text("blocks")
        images = page.get_images()

        page_spans: list[TextSpan] = []
        page_text_pieces: list[str] = []
        page_offset = 0

        # Check for scanned page: minimal text (< 50 chars) and page has images
        page_text_raw = page.get_text("text").strip()
        page_is_ocr = False
        if len(page_text_raw) < 50 and len(images) > 0:
            page_is_ocr = True
            document_is_ocr = True

        for block in raw_blocks:
            # block[4] is the text content
            block_text = block[4].strip()
            if not block_text:
                continue

            # Determine block type (heading vs paragraph)
            block_type = "paragraph"
            if len(block_text) < 100 and (
                re.match(r"^(SECTION|ARTICLE|\d+(\.\d+)*)\b", block_text, re.IGNORECASE) or block_text.isupper()
            ):
                block_type = "heading"

            # Calculate offsets
            span_start_page = page_offset
            span_end_page = span_start_page + len(block_text)
            span_start_doc = current_doc_offset + span_start_page
            span_end_doc = current_doc_offset + span_end_page

            page_spans.append(
                TextSpan(
                    page_number=page_number,
                    char_start_page=span_start_page,
                    char_end_page=span_end_page,
                    char_start_doc=span_start_doc,
                    char_end_doc=span_end_doc,
                    text=block_text,
                    block_type=block_type,
                )
            )

            page_text_pieces.append(block_text)
            page_offset += len(block_text) + 2  # account for double newline separator

        page_combined_text = "\n\n".join(page_text_pieces)
        page_char_start = current_doc_offset
        page_char_end = current_doc_offset + len(page_combined_text)

        pages.append(
            DocumentPage(
                page_number=page_number,
                text=page_combined_text,
                char_start_doc=page_char_start,
                char_end_doc=page_char_end,
                is_ocr=page_is_ocr,
                spans=page_spans,
                metadata={"image_count": len(images), "block_count": len(raw_blocks)},
            )
        )

        full_text_parts.append(page_combined_text)
        current_doc_offset += len(page_combined_text) + 2  # page separator \n\n

    full_document_text = "\n\n".join(full_text_parts)

    return ParsedDocument(
        id=doc_id,
        filename=filename,
        file_type=DocumentFileType.PDF,
        file_size_bytes=len(file_bytes),
        storage_path=storage_path,
        full_text=full_document_text,
        page_count=len(pages),
        is_ocr=document_is_ocr,
        pages=pages,
        metadata={"pdf_producer": pdf_doc.metadata.get("producer", ""), "format": "PDF"},
    )
