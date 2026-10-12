from backend.evidence.verifier import verify_quote_in_page_text


def test_exact_quote_verification():
    sample_page = "Section 3.1: The Recipient shall maintain strict confidentiality for three (3) years."
    quote = "Recipient shall maintain strict confidentiality"
    verified, span = verify_quote_in_page_text(quote, sample_page, page_number=1, char_offset_in_doc=100)
    assert verified is True
    assert span.verified is True
    assert span.page_number == 1
    assert span.char_start == 100 + sample_page.find(quote)
    assert span.char_end == span.char_start + len(quote)
    assert span.rejection_reason is None


def test_whitespace_flexible_verification():
    sample_page = "Section 3.1: The Recipient   shall  \n maintain strict\tconfidentiality."
    quote = "Recipient shall maintain strict confidentiality"
    verified, span = verify_quote_in_page_text(quote, sample_page, page_number=2, char_offset_in_doc=0)
    assert verified is True
    assert span.verified is True
    assert span.page_number == 2


def test_hallucinated_quote_rejected():
    sample_page = "Section 3.1: The Recipient shall maintain strict confidentiality for three (3) years."
    quote = "The Recipient must forfeit all corporate assets immediately upon breach"
    verified, span = verify_quote_in_page_text(quote, sample_page, page_number=1)
    assert verified is False
    assert span.verified is False
    assert "hallucination rejected" in span.rejection_reason.lower()
