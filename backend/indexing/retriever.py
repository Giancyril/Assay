import re
import math
import hashlib
from typing import List, Dict, Tuple, Optional
from backend.indexing.models import ClauseChunk, RetrievalResult


def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into lowercase terms."""
    return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())


def compute_deterministic_pseudo_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Computes a deterministic dense n-gram vector for offline / mock testing
    when an external LLM embedding API is not configured or in unit tests.
    """
    vec = [0.0] * dim
    tokens = tokenize(text)
    if not tokens:
        return vec

    for i in range(len(tokens)):
        # unigram
        h1 = int(hashlib.md5(tokens[i].encode("utf-8")).hexdigest(), 16) % dim
        vec[h1] += 1.0
        # bigram
        if i + 1 < len(tokens):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            h2 = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16) % dim
            vec[h2] += 1.5

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two normalized vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return max(0.0, min(1.0, dot))


class HybridRetriever:
    """
    Hybrid retriever combining full-text search (exact legal terminology & BM25)
    with dense semantic vector similarity.
    """
    def __init__(self, chunks: List[ClauseChunk]):
        self.chunks = chunks
        self._doc_tokens: Dict[str, List[str]] = {}
        self._doc_embeddings: Dict[str, List[float]] = {}
        self._index_chunks()

    def _index_chunks(self):
        for c in self.chunks:
            tokens = tokenize(f"{c.section_title} {c.content}")
            self._doc_tokens[c.id] = tokens
            if c.embedding:
                self._doc_embeddings[c.id] = c.embedding
            else:
                self._doc_embeddings[c.id] = compute_deterministic_pseudo_embedding(f"{c.section_title} {c.content}")

    def fts_search(self, query: str) -> Dict[str, float]:
        """Calculates full-text lexical score with phrase boosting."""
        q_tokens = tokenize(query)
        q_lower = query.lower().strip()
        scores: Dict[str, float] = {}

        if not q_tokens:
            return {c.id: 0.0 for c in self.chunks}

        total_docs = len(self.chunks)
        # Compute term frequencies and document frequencies
        df: Dict[str, int] = {}
        for term in set(q_tokens):
            df[term] = sum(1 for c in self.chunks if term in self._doc_tokens[c.id])

        for c in self.chunks:
            c_tokens = self._doc_tokens[c.id]
            doc_len = len(c_tokens) or 1
            score = 0.0
            
            # BM25-style term weighting
            for term in q_tokens:
                tf = c_tokens.count(term)
                if tf > 0:
                    doc_freq = df.get(term, 1)
                    idf = math.log(1.0 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                    score += idf * (tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * doc_len / 100.0))

            # Exact legal phrase match bonus
            content_lower = c.content.lower()
            if q_lower in content_lower or (len(q_tokens) > 1 and all(t in content_lower for t in q_tokens)):
                score += 3.0

            # Title match bonus
            if any(t in c.section_title.lower() for t in q_tokens):
                score += 2.0

            scores[c.id] = max(0.0, score)

        # Normalize scores to [0, 1]
        max_s = max(scores.values()) if scores and max(scores.values()) > 0 else 1.0
        return {cid: min(1.0, s / max_s) for cid, s in scores.items()}

    def vector_search(self, query: str) -> Dict[str, float]:
        """Calculates dense semantic similarity score."""
        q_vec = compute_deterministic_pseudo_embedding(query)
        scores: Dict[str, float] = {}
        for c in self.chunks:
            c_vec = self._doc_embeddings.get(c.id, [])
            sim = cosine_similarity(q_vec, c_vec)
            scores[c.id] = sim
        return scores

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5
    ) -> List[RetrievalResult]:
        """
        Runs hybrid retrieval combining vector search and FTS.
        alpha=1.0 is vector-only, alpha=0.0 is FTS-only, alpha=0.5 is balanced.
        """
        if not self.chunks:
            return []

        fts_scores = self.fts_search(query)
        vector_scores = self.vector_search(query)

        results: List[RetrievalResult] = []
        for c in self.chunks:
            f_score = fts_scores.get(c.id, 0.0)
            v_score = vector_scores.get(c.id, 0.0)
            combined = (alpha * v_score) + ((1.0 - alpha) * f_score)

            results.append(
                RetrievalResult(
                    chunk=c,
                    vector_score=round(v_score, 4),
                    fts_score=round(f_score, 4),
                    combined_score=round(combined, 4),
                    match_type="hybrid" if f_score > 0 and v_score > 0 else ("fts" if f_score > 0 else "vector")
                )
            )

        # Sort by combined score descending
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results[:top_k]
