import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from app.core.logging import logger


class MemoryVectorStore:
    """In-memory BM25 index backed by persisted SQLite document chunks."""

    def __init__(self, collection_name: Optional[str] = None, load_existing: bool = False):
        self.collection_name = collection_name or "autosar_hld_chunks"
        self._chunks: Dict[str, Dict[str, Any]] = {}
        self._load_existing = load_existing
        if load_existing:
            self.refresh_from_database()

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        for chunk in chunks:
            metadata = dict(chunk.get("metadata") or {})
            metadata.update({
                key: chunk[key]
                for key in (
                    "project_id", "document_id", "document_name", "version_label",
                    "page_number", "section", "chunk_id", "source_type"
                )
                if key in chunk
            })
            chunk_id = str(metadata.get("chunk_id") or chunk.get("id") or "")
            if not chunk_id or "document_id" not in metadata or "text" not in chunk:
                continue

            self._chunks[chunk_id] = {
                "text": str(chunk["text"]),
                "metadata": {
                    "project_id": str(metadata.get("project_id", "P001")),
                    "document_id": str(metadata["document_id"]),
                    "document_name": str(metadata.get("document_name", "")),
                    "version_label": str(metadata.get("version_label", "v1.0")),
                    "page_number": int(metadata.get("page_number", metadata.get("page", 1))),
                    "section": str(metadata.get("section", "General")),
                    "chunk_id": chunk_id,
                    "source_type": str(metadata.get("source_type", "HLD")),
                },
            }

    def refresh_from_database(self) -> None:
        from app.db.models import Document, DocumentChunk
        from app.db.repositories import SessionLocal

        session = SessionLocal()
        try:
            rows = (
                session.query(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .all()
            )
            self._chunks.clear()
            self.add_chunks([
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_name": document.name,
                    "version_label": document.version_label,
                    "project_id": document.project_id,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text,
                    "source_type": document.source_type,
                }
                for chunk, document in rows
            ])
        except Exception as error:
            logger.warning(f"Could not refresh the in-memory retrieval index from SQLite: {error}")
        finally:
            session.close()

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"[a-z0-9_]+", text.lower())

    def search(
        self,
        query: str,
        top_k: int = 8,
        project_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if self._load_existing:
            self.refresh_from_database()

        query_terms = self._tokens(query)
        if not query_terms or top_k <= 0:
            return []

        allowed_documents = set(document_ids) if document_ids else None
        candidates = []
        for chunk_id, chunk in self._chunks.items():
            metadata = chunk["metadata"]
            if project_id and metadata["project_id"] != project_id:
                continue
            if allowed_documents and metadata["document_id"] not in allowed_documents:
                continue
            tokens = self._tokens(chunk["text"])
            if tokens:
                candidates.append((chunk_id, chunk, tokens, Counter(tokens)))

        if not candidates:
            return []

        document_count = len(candidates)
        average_length = sum(len(item[2]) for item in candidates) / document_count
        document_frequency = Counter(
            term
            for _, _, _, term_counts in candidates
            for term in set(term_counts)
        )
        query_frequency = Counter(query_terms)
        results = []

        for insertion_order, (chunk_id, chunk, tokens, term_counts) in enumerate(candidates):
            document_length = len(tokens)
            score = 0.0
            for term, query_count in query_frequency.items():
                frequency = term_counts.get(term, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log(
                    1 + (document_count - document_frequency[term] + 0.5)
                    / (document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.5 * (
                    1 - 0.75 + 0.75 * document_length / max(average_length, 1.0)
                )
                score += query_count * inverse_frequency * (frequency * 2.5) / denominator

            if score <= 0:
                continue
            results.append((score, insertion_order, chunk_id, chunk))

        results.sort(key=lambda item: (-item[0], item[1]))
        return [
            {
                "chunk_id": chunk_id,
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "similarity_score": round(score / (score + 1), 4),
            }
            for score, _, chunk_id, chunk in results[:top_k]
        ]


VectorStore = MemoryVectorStore
