"""
Standalone Retrieval Evaluation Script.
Evaluates hybrid clause retrieval accuracy across synthetic benchmark contracts.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion.service import ingest_document_bytes
from backend.indexing.chunker import chunk_document_by_structure
from backend.indexing.retriever import HybridRetriever

BENCHMARK_QUERIES = [
    ("Governing Law", "governing law State of Delaware jurisdiction", "6"),
    ("Non-Solicitation", "directly or indirectly solicit recruit hire personnel", "8"),
    ("Confidentiality Term", "expire three years survive termination duration", "3"),
    ("Return of Materials", "promptly return or certify destruction archival backup", "4"),
    ("Carve-outs / Exclusions", "publicly known prior possession independently developed", "1"),
    ("Equitable Remedies", "irreparable harm injunctive relief without bond", "7"),
    ("Compelled Disclosure", "valid subpoena court order prompt written notice", "5"),
    ("Standard of Care", "exercise reasonable care to maintain confidentiality", "2")
]

def run_retrieval_benchmark():
    import pymupdf
    from tests.unit.test_retrieval import SAMPLE_CONTRACT_TEXT
    
    doc_pdf = pymupdf.open()
    page = doc_pdf.new_page()
    page.insert_text((50, 72), SAMPLE_CONTRACT_TEXT, fontsize=10)
    pdf_bytes = doc_pdf.tobytes()
    doc_pdf.close()
    
    parsed_doc = ingest_document_bytes(pdf_bytes, "eval_benchmark_nda.pdf")
    chunks = chunk_document_by_structure(parsed_doc)
    retriever = HybridRetriever(chunks)
    
    hits_at_1 = 0
    hits_at_3 = 0
    rr_scores = []
    
    print("\n================== HYBRID RETRIEVAL BENCHMARK ==================")
    print(f"Document: {parsed_doc.filename} | Total Chunks: {len(chunks)}\n")
    
    for name, query, expected_sec in BENCHMARK_QUERIES:
        results = retriever.retrieve(query=query, top_k=3, alpha=0.5)
        ranks = [r.chunk.section_number for r in results]
        
        found_rank = None
        for i, r in enumerate(results, start=1):
            if r.chunk.section_number == expected_sec:
                found_rank = i
                break
                
        status_sym = "[OK]" if found_rank == 1 else ("[WARN]" if found_rank else "[FAIL]")
        rank_str = f"Rank {found_rank}" if found_rank else "Not in top 3"
        print(f"{status_sym} {name:<25} -> Expected Sec {expected_sec} | Got {rank_str} (Top: {ranks})")
        
        if found_rank == 1:
            hits_at_1 += 1
        if found_rank and found_rank <= 3:
            hits_at_3 += 1
        if found_rank:
            rr_scores.append(1.0 / found_rank)
        else:
            rr_scores.append(0.0)
            
    total = len(BENCHMARK_QUERIES)
    recall_1 = hits_at_1 / total
    recall_3 = hits_at_3 / total
    mrr = sum(rr_scores) / total
    
    print("\n------------------------- SUMMARY METRICS -------------------------")
    print(f"Recall@1: {recall_1 * 100:.1f}%")
    print(f"Recall@3: {recall_3 * 100:.1f}%")
    print(f"MRR:      {mrr:.4f}")
    print("===================================================================\n")
    return recall_1, recall_3, mrr

if __name__ == "__main__":
    r1, r3, mrr = run_retrieval_benchmark()
    if r1 < 0.9:
        sys.exit(1)
