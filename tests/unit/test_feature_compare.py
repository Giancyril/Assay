from fastapi.testclient import TestClient

from backend.app.main import app
from backend.compare.engine import ComparativeConflictEngine
from backend.compare.models import ConflictSeverity, ConflictType
from backend.ingestion.models import DocumentFileType, ParsedDocument
from backend.ingestion.repository import doc_repository

client = TestClient(app)


def _make_dummy_doc(doc_id: str, filename: str, text: str) -> ParsedDocument:
    return ParsedDocument(
        id=doc_id,
        filename=filename,
        file_type=DocumentFileType.PDF,
        file_size_bytes=len(text.encode("utf-8")),
        storage_path=f"/tmp/{filename}",
        page_count=1,
        full_text=text,
        metadata={"title": filename},
    )


def test_compare_aligned_documents():
    text = (
        "This Agreement shall be governed by the laws of the State of Delaware. "
        "The confidentiality term shall be 3 years. "
        "Either party may terminate upon 30 days notice. "
        "Confidential information must be marked confidential."
    )
    doc_a = _make_dummy_doc("doc-a-1", "msa.pdf", text)
    doc_b = _make_dummy_doc("doc-b-1", "sow.pdf", text)

    result = ComparativeConflictEngine.compare(doc_a, doc_b)
    assert result.total_conflicts == 0
    assert result.alignment_score == 100.0
    assert len(result.clause_comparisons) == 4
    assert all(not item.has_conflict for item in result.clause_comparisons)


def test_compare_jurisdiction_mismatch():
    text_a = "Governing Law: This Agreement shall be governed by Delaware law."
    text_b = "Governing Law: This Agreement is governed by California law."
    doc_a = _make_dummy_doc("doc-a-2", "primary.pdf", text_a)
    doc_b = _make_dummy_doc("doc-b-2", "addendum.pdf", text_b)

    result = ComparativeConflictEngine.compare(doc_a, doc_b)
    assert result.critical_conflicts == 1
    jur_conflict = next(c for c in result.conflicts if c.conflict_type == ConflictType.GOVERNING_LAW_MISMATCH)
    assert jur_conflict.severity == ConflictSeverity.CRITICAL
    assert "Delaware" in jur_conflict.doc_a_excerpt
    assert "California" in jur_conflict.doc_b_excerpt
    assert result.alignment_score <= 75.0


def test_compare_duration_mismatch():
    text_a = "The confidentiality obligations shall survive for 2 years following disclosure."
    text_b = "Confidentiality obligations shall survive in perpetual duration."
    doc_a = _make_dummy_doc("doc-a-3", "doc_a.pdf", text_a)
    doc_b = _make_dummy_doc("doc-b-3", "doc_b.pdf", text_b)

    result = ComparativeConflictEngine.compare(doc_a, doc_b)
    assert result.high_conflicts >= 1
    dur_conflict = next(c for c in result.conflicts if c.conflict_type == ConflictType.DURATION_MISMATCH)
    assert dur_conflict.severity == ConflictSeverity.HIGH
    assert "2 years" in dur_conflict.doc_a_excerpt
    assert "Perpetual" in dur_conflict.doc_b_excerpt


def test_compare_notice_period_mismatch():
    text_a = "Either party may terminate this agreement with 30 days written notice."
    text_b = "Termination requires at least 90 days notice."
    doc_a = _make_dummy_doc("doc-a-4", "doc_a.pdf", text_a)
    doc_b = _make_dummy_doc("doc-b-4", "doc_b.pdf", text_b)

    result = ComparativeConflictEngine.compare(doc_a, doc_b)
    not_conflict = next(c for c in result.conflicts if c.conflict_type == ConflictType.NOTICE_PERIOD_MISMATCH)
    assert not_conflict.severity == ConflictSeverity.MEDIUM
    assert "30" in not_conflict.doc_a_excerpt
    assert "90" in not_conflict.doc_b_excerpt


def test_compare_marking_mismatch():
    text_a = "Information must be marked confidential at time of disclosure."
    text_b = "All proprietary information receives automatic protection without marking."
    doc_a = _make_dummy_doc("doc-a-5", "doc_a.pdf", text_a)
    doc_b = _make_dummy_doc("doc-b-5", "doc_b.pdf", text_b)

    result = ComparativeConflictEngine.compare(doc_a, doc_b)
    mark_conflict = next(c for c in result.conflicts if c.conflict_type == ConflictType.CONFIDENTIALITY_SCOPE_MISMATCH)
    assert mark_conflict.severity == ConflictSeverity.HIGH


def test_compare_api_not_found():
    res = client.post("/api/compare/audit", json={"doc_a_id": "nonexistent-1", "doc_b_id": "nonexistent-2"})
    assert res.status_code == 404
    assert "Primary document" in res.json()["detail"]


def test_compare_api_roundtrip():
    doc_a = _make_dummy_doc("cmp-doc-1", "vendor_a.pdf", "Governed by Delaware. 30 days notice.")
    doc_b = _make_dummy_doc("cmp-doc-2", "vendor_b.pdf", "Governed by New York. 60 days notice.")
    doc_repository._memory_cache[doc_a.id] = doc_a
    doc_repository._memory_cache[doc_b.id] = doc_b

    res = client.post(
        "/api/compare/audit",
        json={"doc_a_id": "cmp-doc-1", "doc_b_id": "cmp-doc-2", "doc_a_role": "MSA", "doc_b_role": "SOW"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_conflicts"] >= 2
    assert "comparison_id" in data
    comp_id = data["comparison_id"]

    # Test GET by comparison_id
    get_res = client.get(f"/api/compare/{comp_id}")
    assert get_res.status_code == 200
    assert get_res.json()["comparison_id"] == comp_id

    # Test 404 on unknown comparison_id
    not_found = client.get("/api/compare/unknown-comp-999")
    assert not_found.status_code == 404
