from fastapi import HTTPException, status

from backend.indexing.chunker import chunk_document_by_structure
from backend.indexing.models import ClauseChunk, RetrievalResult
from backend.indexing.retriever import HybridRetriever
from backend.ingestion.repository import doc_repository


class ClauseIndexService:
    def __init__(self):
        # Cache of document_id -> list of ClauseChunks
        self._document_clauses: dict[str, list[ClauseChunk]] = {}
        # Cache of document_id -> HybridRetriever instance
        self._document_retrievers: dict[str, HybridRetriever] = {}

    def index_document(self, doc_id: str) -> list[ClauseChunk]:
        """Extracts structure-aware clauses and builds hybrid search index for a document."""
        doc = doc_repository.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

        chunks = chunk_document_by_structure(doc)
        self._document_clauses[doc_id] = chunks
        self._document_retrievers[doc_id] = HybridRetriever(chunks)
        return chunks

    def get_document_clauses(self, doc_id: str) -> list[ClauseChunk]:
        """Returns indexed clauses for a document, indexing automatically if not already done."""
        if doc_id not in self._document_clauses:
            return self.index_document(doc_id)
        return self._document_clauses[doc_id]

    def search_document(self, doc_id: str, query: str, top_k: int = 5, alpha: float = 0.5) -> list[RetrievalResult]:
        """Performs hybrid retrieval against a document's indexed clauses."""
        if doc_id not in self._document_retrievers:
            self.index_document(doc_id)

        retriever = self._document_retrievers[doc_id]
        return retriever.retrieve(query=query, top_k=top_k, alpha=alpha)


clause_index_service = ClauseIndexService()
