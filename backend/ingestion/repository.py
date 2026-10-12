import os
import json
import shutil
from typing import List, Optional, Dict
from backend.app.config import settings
from backend.ingestion.models import ParsedDocument, DocumentPage, TextSpan


class DocumentRepository:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        self._memory_cache: Dict[str, ParsedDocument] = {}
        self._load_existing_manifests()

    def _load_existing_manifests(self):
        """Scan upload directory for persisted document manifests on startup."""
        if not os.path.exists(self.base_dir):
            return
        for entry in os.listdir(self.base_dir):
            doc_dir = os.path.join(self.base_dir, entry)
            manifest_path = os.path.join(doc_dir, "manifest.json")
            if os.path.isdir(doc_dir) and os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        parsed = ParsedDocument.model_validate(data)
                        self._memory_cache[parsed.id] = parsed
                except Exception:
                    pass

    def save_document(self, doc: ParsedDocument, raw_bytes: bytes) -> ParsedDocument:
        doc_dir = os.path.join(self.base_dir, doc.id)
        os.makedirs(doc_dir, exist_ok=True)

        # 1. Save original file
        ext = doc.file_type.value
        original_path = os.path.join(doc_dir, f"original.{ext}")
        with open(original_path, "wb") as f:
            f.write(raw_bytes)
        doc.storage_path = original_path

        # 2. Save extracted text
        text_path = os.path.join(doc_dir, "extracted_text.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(doc.full_text)

        # 3. Save full manifest
        manifest_path = os.path.join(doc_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(doc.model_dump_json(indent=2))

        # 4. Cache in memory
        self._memory_cache[doc.id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[ParsedDocument]:
        return self._memory_cache.get(doc_id)

    def list_documents(self) -> List[ParsedDocument]:
        return list(self._memory_cache.values())

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._memory_cache:
            del self._memory_cache[doc_id]
        doc_dir = os.path.join(self.base_dir, doc_id)
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir, ignore_errors=True)
            return True
        return False


# Global singleton instance
doc_repository = DocumentRepository()
