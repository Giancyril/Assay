from fastapi.testclient import TestClient

from backend.app.main import app
from backend.indexing.chunker import chunk_document_by_structure
from backend.indexing.retriever import HybridRetriever
from backend.ingestion.service import ingest_document_bytes

client = TestClient(app)

SAMPLE_CONTRACT_TEXT = """MUTUAL NON-DISCLOSURE AGREEMENT
This Agreement is entered into on October 12, 2026.

1. DEFINITIONS.
"Confidential Information" refers to any proprietary data disclosed by Discloser to Recipient.
Confidential Information does not include information that: (a) is or becomes publicly known;
(b) was already in Recipient's possession prior to disclosure; or (c) is independently developed.

2. DUTY OF CARE.
Recipient agrees to exercise reasonable care to maintain confidentiality of Discloser's information.

3. TERM AND TERMINATION.
The confidentiality obligations set forth herein shall survive termination and expire three (3) years from disclosure.

4. RETURN OF CONFIDENTIAL MATERIALS.
Upon written request, Recipient shall promptly return or certify destruction of all Confidential Information, provided that routine archival IT backups may be retained.

5. PERMITTED COMPELLED DISCLOSURE.
Recipient may disclose Confidential Information pursuant to a valid subpoena or court order, provided prompt written notice is provided where legally permissible.

6. GOVERNING LAW AND JURISDICTION.
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles.

7. EQUITABLE REMEDIES.
Breach of this Agreement may cause irreparable harm for which damages are inadequate, entitling Discloser to seek injunctive relief without bond.

8. NON-SOLICITATION OF PERSONNEL.
Recipient agrees that during the term and for eighteen (18) months thereafter, Recipient shall not directly or indirectly solicit, recruit, or hire any officer or employee of Discloser.
"""

def create_ingested_test_doc():
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), SAMPLE_CONTRACT_TEXT, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return ingest_document_bytes(pdf_bytes, "test_retrieval_nda.pdf")


def test_structure_aware_chunking():
    doc = create_ingested_test_doc()
    chunks = chunk_document_by_structure(doc)

    assert len(chunks) >= 8, f"Expected at least 8 clauses, got {len(chunks)}"

    # Check section numbers and titles
    sec_map = {c.section_number: c.section_title for c in chunks if c.section_number}
    assert "1" in sec_map and "DEFINITIONS" in sec_map["1"].upper()
    assert "3" in sec_map and "TERM" in sec_map["3"].upper()
    assert "6" in sec_map and "GOVERNING LAW" in sec_map["6"].upper()
    assert "8" in sec_map and "NON-SOLICITATION" in sec_map["8"].upper()

    # Check offset accuracy: full_text slice must match chunk content
    for c in chunks:
        sliced = doc.full_text[c.char_start_doc:c.char_end_doc]
        assert sliced == c.content, "Chunk offset slice does not match content"


def test_retrieval_accuracy_evaluation_before_llm():
    """
    Evaluates retrieval on its own first (as per Phase 2 spec):
    verifies that targeted compliance queries return the ground-truth clause at Rank 1.
    """
    doc = create_ingested_test_doc()
    chunks = chunk_document_by_structure(doc)
    retriever = HybridRetriever(chunks)

    test_cases = [
        {
            "query": "governing law State of Delaware and jurisdiction",
            "expected_section": "6",
            "description": "Governing Law clause"
        },
        {
            "query": "solicit, recruit, or hire any officer or employee non-solicitation",
            "expected_section": "8",
            "description": "Non-solicitation clause"
        },
        {
            "query": "confidentiality obligations survive expire three (3) years duration",
            "expected_section": "3",
            "description": "Term / Duration clause"
        },
        {
            "query": "return or certify destruction of all Confidential Information",
            "expected_section": "4",
            "description": "Return of Materials clause"
        },
        {
            "query": "carve-outs publicly known prior possession independently developed",
            "expected_section": "1",
            "description": "Exceptions / Definitions clause"
        }
    ]

    rank_1_hits = 0
    reciprocal_ranks = []

    for tc in test_cases:
        results = retriever.retrieve(query=tc["query"], top_k=3, alpha=0.5)
        assert len(results) > 0, f"No results for query '{tc['query']}'"

        # Check rank of expected section
        found_rank = None
        for rank, res in enumerate(results, start=1):
            if res.chunk.section_number == tc["expected_section"]:
                found_rank = rank
                break

        assert found_rank is not None, f"Expected section {tc['expected_section']} not found in top 3 for {tc['description']}"
        reciprocal_ranks.append(1.0 / found_rank)
        if found_rank == 1:
            rank_1_hits += 1

    recall_at_1 = rank_1_hits / len(test_cases)
    mrr = sum(reciprocal_ranks) / len(test_cases)

    # Assert high accuracy for hybrid retrieval
    assert recall_at_1 == 1.0, f"Recall@1 expected 1.0, got {recall_at_1}"
    assert mrr == 1.0, f"MRR expected 1.0, got {mrr}"


def test_indexing_api_endpoints():
    doc = create_ingested_test_doc()

    # 1. Trigger indexing
    idx_res = client.post(f"/api/documents/{doc.id}/index")
    assert idx_res.status_code == 200
    clauses = idx_res.json()
    assert len(clauses) >= 8

    # 2. Get clauses
    get_res = client.get(f"/api/documents/{doc.id}/clauses")
    assert get_res.status_code == 200
    assert len(get_res.json()) == len(clauses)

    # 3. Search clauses
    search_res = client.post(
        f"/api/documents/{doc.id}/search",
        json={"query": "laws of the State of Delaware", "top_k": 3}
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert results[0]["chunk"]["section_number"] == "6"
    assert results[0]["combined_score"] > 0
